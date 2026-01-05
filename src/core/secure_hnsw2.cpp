/**
 * secure_hnsw2.cpp
 * Variant 2: Hybrid Encrypted HNSW with Partial Client Decryption
 * 
 * Strategy:
 * - Cloud computes ALL distance-related operations homomorphically
 * - Client partially decrypts intermediate encrypted distances (e.g., cluster distances or HNSW layer candidates)
 * - Client decides the next navigation step based on decrypted distances
 * - Communication overhead is tracked
 */

#pragma once

#include <vector>
#include <queue>
#include <random>
#include <unordered_set>
#include <algorithm>
#include <iostream>
#include "seal_utils.cpp"
#include "poly_softmin.cpp"

namespace pprag {

struct HNSWNode2 {
    int id;
    int level;
};

/**
 * Variant 2: Hybrid HNSW with Partial Client-Side Decryption
 * 
 * Key differences from SecureHNSWEncrypted:
 * 1. Server computes encrypted distances for ALL candidates in a layer
 * 2. Server sends encrypted distances to client
 * 3. Client decrypts intermediate distances and returns sorted candidate indices
 * 4. Communication cost is tracked (size of encrypted distances transmitted)
 * 5. Navigation decisions are made by client based on decrypted intermediate results
 */
class SecureHNSWEncrypted2 {
public:
    SecureHNSWEncrypted2(CKKSContext& ctx, int M = 16, int ef_construction = 200, int ef_search = 100)
        : ctx_(ctx), M_(M), ef_construction_(ef_construction), ef_search_(ef_search),
          max_level_(0), entry_point_(-1), softmin_(4, 1.0), total_comm_bytes_(0) {
        level_mult_ = 1.0 / std::log(M_);
    }
    
    // Store encrypted vectors
    void add_encrypted_node(int id, const Ciphertext& vec, int level) {
        if (id >= node_vectors_.size()) {
            node_vectors_.resize(id + 1);
            nodes_.resize(id + 1);
        }
        node_vectors_[id] = vec; // Copy ciphertext
        
        nodes_[id].id = id;
        nodes_[id].level = level;
        nodes_[id].neighbors.resize(level + 1);
        
        if (entry_point_ < 0) {
            entry_point_ = id;
            max_level_ = level;
        }
    }
    
    /**
     * Distance between query (encrypted) and node (encrypted)
     * Returns encrypted distance^2
     */
    Ciphertext encrypted_distance_sq(const Ciphertext& query, int node_id) {
        return he_squared_distance(query, node_vectors_[node_id], ctx_);
    }
    
    /**
     * Estimate communication cost: size of one encrypted distance
     * In CKKS, each Ciphertext has approximately:
     * - For each coefficient: ~4 bytes (assuming 64-bit integers mod p)
     * - Poly degree typically 8192
     * - With 2 moduli in chain: ~8192 * 8 bytes = 65KB per ciphertext
     * This is a rough estimate.
     */
    static constexpr size_t CIPHERTEXT_SIZE_BYTES = 65536; // 64KB per encrypted distance
    
    struct EncryptedDistanceData {
        std::vector<Ciphertext> distances; // encrypted distances to candidates
        std::vector<int> candidate_ids;   // corresponding node IDs
    };
    
    /**
     * Layer search with client-aided partial decryption
     * 
     * Variant2 Protocol:
     * 1. Cloud computes encrypted distances for ef candidates in layer
     * 2. Cloud sends (encrypted_distances, candidate_ids) to client
     * 3. Client decrypts distances and returns top-ef sorted by distance
     * 4. Cloud continues navigation with client's decision
     */
    std::vector<int> search(const Ciphertext& query, int k) {
        if (entry_point_ < 0) return {};
        
        int curr = entry_point_;
        
        // Traverse upper levels
        for (int l = max_level_; l >= 1; --l) {
            curr = greedy_search_layer_v2(query, curr, 1, l)[0];
        }
        
        // Bottom layer search with ef_search_
        auto candidates = greedy_search_layer_v2(query, curr, ef_search_, 0);
        
        // Return top-k
        if (candidates.size() > k) candidates.resize(k);
        return candidates;
    }
    
    // Get total communication cost in bytes
    size_t get_communication_bytes() const {
        return total_comm_bytes_;
    }
    
    // Reset communication counter
    void reset_communication_counter() {
        total_comm_bytes_ = 0;
    }
    
    // Internal node structure
    struct NodeInfo {
        int id;
        int level;
        std::vector<std::vector<int>> neighbors;
    };
    
private:
    /**
     * Variant 2: Layer search with simulated client-aided decryption
     * 
     * Flow:
     * 1. Server: Compute encrypted distances for neighbors (server-side)
     * 2. Server: Send encrypted distances to client (count communication)
     * 3. Client: Decrypt intermediate distances and pick next candidates
     * 4. Continue with selected candidates
     */
    std::vector<int> greedy_search_layer_v2(const Ciphertext& query, int entry, int ef, int level) {
        std::unordered_set<int> visited;
        std::priority_queue<std::pair<double, int>> candidates; // max-heap by negative distance
        std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>, std::greater<>> results; // min-heap
        
        // Variant2: Entry point distance is decrypted (client-side)
        double entry_dist = decrypt_and_get_dist(query, entry);
        
        candidates.push({-entry_dist, entry});
        results.push({entry_dist, entry});
        visited.insert(entry);
        
        while (!candidates.empty()) {
            auto [neg_dist, curr] = candidates.top();
            candidates.pop();
            
            if (-neg_dist > results.top().first && results.size() >= ef) break;
            
            // Step 1: Server computes encrypted distances for all neighbors
            const auto& neighbors = nodes_[curr].neighbors[level];
            std::vector<int> unvisited_neighbors;
            std::vector<Ciphertext> encrypted_distances;
            
            for (int neighbor : neighbors) {
                if (visited.count(neighbor)) continue;
                unvisited_neighbors.push_back(neighbor);
                // Server: Compute encrypted distance
                Ciphertext enc_dist = encrypted_distance_sq(query, neighbor);
                encrypted_distances.push_back(enc_dist);
            }
            
            // Step 2: Simulate client-side decryption of intermediate distances
            // Communication cost: size of encrypted_distances sent to client
            total_comm_bytes_ += encrypted_distances.size() * CIPHERTEXT_SIZE_BYTES;
            
            // Step 3: Client decrypts and evaluates, decides next candidates
            for (size_t i = 0; i < unvisited_neighbors.size(); ++i) {
                int neighbor = unvisited_neighbors[i];
                visited.insert(neighbor);
                
                // Client decrypts the distance
                double dist = decrypt_ciphertext(encrypted_distances[i]);
                
                // Client-side decision: add to candidates if promising
                if (results.size() < ef || dist < results.top().first) {
                    candidates.push({-dist, neighbor});
                    results.push({dist, neighbor});
                }
            }
        }
        
        std::vector<int> res_vec;
        while (!results.empty()) {
            res_vec.push_back(results.top().second);
            results.pop();
        }
        std::reverse(res_vec.begin(), res_vec.end());
        return res_vec;
    }
    
    double decrypt_and_get_dist(const Ciphertext& query, int id) {
        Ciphertext dist_enc = encrypted_distance_sq(query, id);
        std::vector<double> plain = ctx_.decrypt_vector(dist_enc);
        return plain[0];
    }
    
    double decrypt_ciphertext(const Ciphertext& ct) {
        std::vector<double> plain = ctx_.decrypt_vector(ct);
        return plain[0];
    }

    CKKSContext& ctx_;
    int M_, ef_construction_, ef_search_;
    double level_mult_;
    int max_level_;
    int entry_point_;
    
    // Storage
    std::vector<Ciphertext> node_vectors_; // Index is ID
    std::vector<NodeInfo> nodes_;
    PolySoftmin softmin_;
    
    // Communication tracking
    size_t total_comm_bytes_;
};

} // namespace pprag

