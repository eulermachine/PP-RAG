/**
 * seal_utils.cpp
 * CKKS utility wrappers - full implementation
 *
 * Provides encryption, decryption and homomorphic operation interfaces
 * https://github.com/microsoft/SEAL
 */

#pragma once

#include <vector>
#include <memory>
#include <stdexcept>
#include <cmath>

#ifdef USE_SEAL
#include "seal/seal.h"
using namespace seal;
#endif

namespace pprag {

/**
 * CKKS encryption context manager
 */
class CKKSContext {
public:
    CKKSContext(
        size_t poly_modulus_degree = 8192, 
        double scale = pow(2.0, 40),
        std::vector<int> coeff_modulus_bits = {60, 40, 40, 60}
    ) : scale_(scale), poly_degree_(poly_modulus_degree) {
        #ifdef USE_SEAL
        EncryptionParameters parms(scheme_type::ckks);
        parms.set_poly_modulus_degree(poly_modulus_degree);
        parms.set_coeff_modulus(CoeffModulus::Create(poly_modulus_degree, coeff_modulus_bits));
        
        context_ = std::make_shared<SEALContext>(parms);
        keygen_ = std::make_shared<KeyGenerator>(*context_);
        
        secret_key_ = keygen_->secret_key();
        keygen_->create_public_key(public_key_);
        keygen_->create_relin_keys(relin_keys_);
        keygen_->create_galois_keys(galois_keys_);
        
        encryptor_ = std::make_shared<Encryptor>(*context_, public_key_);
        decryptor_ = std::make_shared<Decryptor>(*context_, secret_key_);
        evaluator_ = std::make_shared<Evaluator>(*context_);
        encoder_ = std::make_shared<CKKSEncoder>(*context_);
        #endif
    }
    
    // ==================== Basic info ====================
    
    size_t slot_count() const {
        #ifdef USE_SEAL
        return encoder_->slot_count();
        #else
        return poly_degree_ / 2;
        #endif
    }
    
    double scale() const { return scale_; }
    size_t poly_degree() const { return poly_degree_; }
    
    // ==================== Encryption / Decryption ====================
    
    #ifdef USE_SEAL
    /**
     * Encrypt a single vector
     */
    Ciphertext encrypt_vector(const std::vector<double>& vec) {
        Plaintext plain;
        encoder_->encode(vec, scale_, plain);
        
        Ciphertext encrypted;
        encryptor_->encrypt(plain, encrypted);
        return encrypted;
    }
    
    /**
     * Batch encrypt multiple vectors (each vector packed into one ciphertext)
     */
    std::vector<Ciphertext> encrypt_batch(const std::vector<std::vector<double>>& vectors) {
        std::vector<Ciphertext> result;
        result.reserve(vectors.size());
        
        for (const auto& vec : vectors) {
            result.push_back(encrypt_vector(vec));
        }
        return result;
    }
    
    /**
     * Decrypt to a vector
     */
    std::vector<double> decrypt_vector(const Ciphertext& ct, size_t length = 0) {
        Plaintext plain;
        decryptor_->decrypt(ct, plain);
        
        std::vector<double> result;
        encoder_->decode(plain, result);
        
        if (length > 0 && length < result.size()) {
            result.resize(length);
        }
        return result;
    }
    
    // ==================== Homomorphic operations ====================
    
    /**
     * Homomorphic addition
     */
    Ciphertext he_add(const Ciphertext& ct1, const Ciphertext& ct2) {
        Ciphertext result;
        evaluator_->add(ct1, ct2, result);
        return result;
    }
    
    void he_add_inplace(Ciphertext& ct1, const Ciphertext& ct2) {
        evaluator_->add_inplace(ct1, ct2);
    }
    
    /**
     * Homomorphic multiplication (requires relinearize and rescale)
     */
    Ciphertext he_multiply(const Ciphertext& ct1, const Ciphertext& ct2) {
        Ciphertext result;
        evaluator_->multiply(ct1, ct2, result);
        evaluator_->relinearize_inplace(result, relin_keys_);
        evaluator_->rescale_to_next_inplace(result);
        return result;
    }
    
    /**
     * Multiply by plaintext scalar
     */
    Ciphertext he_multiply_plain(const Ciphertext& ct, double scalar) {
        Plaintext plain;
        encoder_->encode(scalar, ct.parms_id(), ct.scale(), plain);
        
        Ciphertext result;
        evaluator_->multiply_plain(ct, plain, result);
        evaluator_->rescale_to_next_inplace(result);
        return result;
    }
    
    /**
     * Homomorphic subtraction
     */
    Ciphertext he_subtract(const Ciphertext& ct1, const Ciphertext& ct2) {
        Ciphertext result;
        evaluator_->sub(ct1, ct2, result);
        return result;
    }
    
    /**
     * Homomorphic squaring
     */
    Ciphertext he_square(const Ciphertext& ct) {
        Ciphertext result;
        evaluator_->square(ct, result);
        evaluator_->relinearize_inplace(result, relin_keys_);
        evaluator_->rescale_to_next_inplace(result);
        return result;
    }
    
    /**
     * Vector rotation
     */
    Ciphertext he_rotate(const Ciphertext& ct, int steps) {
        Ciphertext result;
        evaluator_->rotate_vector(ct, steps, galois_keys_, result);
        return result;
    }
    
    // ==================== Composite operations ====================
    
    /**
     * Homomorphic inner product computation
     * Uses multiply + rotate-and-sum pattern
     */
    Ciphertext he_inner_product(const Ciphertext& ct1, const Ciphertext& ct2) {
        // Element-wise multiplication
        Ciphertext result = he_multiply(ct1, ct2);
        
        // Rotate and sum to get inner product
        size_t slots = slot_count();
        for (size_t i = 1; i < slots; i *= 2) {
            Ciphertext rotated = he_rotate(result, static_cast<int>(i));
            // Align scales and add
            match_scale_and_add_inplace(result, rotated);
        }
        
        return result;
    }
    
    /**
     * Compute squared L2 distance: ||a - b||^2
     */
    Ciphertext he_l2_distance_squared(const Ciphertext& ct1, const Ciphertext& ct2) {
        // diff = ct1 - ct2
        Ciphertext diff = he_subtract(ct1, ct2);
        // diff^2
        Ciphertext diff_sq = he_square(diff);
        
        // sum all slots
        size_t slots = slot_count();
        for (size_t i = 1; i < slots; i *= 2) {
            Ciphertext rotated = he_rotate(diff_sq, static_cast<int>(i));
            match_scale_and_add_inplace(diff_sq, rotated);
        }
        
        return diff_sq;
    }
    
    // ==================== Helper functions ====================
    
    /**
     * Match scales and add in-place
     */
    void match_scale_and_add_inplace(Ciphertext& ct1, Ciphertext& ct2) {
        // Match parms_id
        if (ct1.parms_id() != ct2.parms_id()) {
            // Switch to the lower level
            auto ctx_data1 = context_->get_context_data(ct1.parms_id());
            auto ctx_data2 = context_->get_context_data(ct2.parms_id());
            
            if (ctx_data1->chain_index() > ctx_data2->chain_index()) {
                evaluator_->mod_switch_to_inplace(ct1, ct2.parms_id());
            } else {
                evaluator_->mod_switch_to_inplace(ct2, ct1.parms_id());
            }
        }
        
        // Match scales
        ct1.scale() = scale_;
        ct2.scale() = scale_;
        
        evaluator_->add_inplace(ct1, ct2);
    }
    
    /**
     * Get ciphertext noise budget (for debugging)
     */
    int noise_budget(const Ciphertext& ct) {
        return decryptor_->invariant_noise_budget(ct);
    }
    
    // Public accessors (for other modules)
    std::shared_ptr<SEALContext> context() { return context_; }
    std::shared_ptr<Evaluator> evaluator() { return evaluator_; }
    std::shared_ptr<CKKSEncoder> encoder() { return encoder_; }
    const RelinKeys& relin_keys() { return relin_keys_; }
    const GaloisKeys& galois_keys() { return galois_keys_; }
    
    #endif  // USE_SEAL
    
private:
    #ifdef USE_SEAL
    std::shared_ptr<SEALContext> context_;
    std::shared_ptr<KeyGenerator> keygen_;
    SecretKey secret_key_;
    PublicKey public_key_;
    RelinKeys relin_keys_;
    GaloisKeys galois_keys_;
    std::shared_ptr<Encryptor> encryptor_;
    std::shared_ptr<Decryptor> decryptor_;
    std::shared_ptr<Evaluator> evaluator_;
    std::shared_ptr<CKKSEncoder> encoder_;
    #endif
    
    double scale_;
    size_t poly_degree_;
};

} // namespace pprag

// Convenience wrapper for secure_hnsw usage
#ifdef USE_SEAL
namespace pprag {
    Ciphertext he_squared_distance(const Ciphertext& a, const Ciphertext& b, CKKSContext& ctx) {
        return ctx.he_l2_distance_squared(a, b);
    }
}
#endif
