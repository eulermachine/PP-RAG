/**
 * secure_kmeans.cpp
 * 安全K-Means聚类实现
 * 
 * 使用PolySoftmin进行软分配
 * 使用HomoNorm进行质心归一化
 */

#pragma once

#include <vector>
#include <random>
#include <algorithm>
#include "poly_softmin.cpp"
#include "homo_norm.cpp"

namespace pprag {

/**
 * 安全K-Means聚类器
 */
class SecureKMeans {
public:
    SecureKMeans(int n_clusters = 100, int max_iter = 10, 
                 double temperature = 1.0, int softmin_degree = 4)
        : n_clusters_(n_clusters), max_iter_(max_iter),
          softmin_(softmin_degree, temperature), homo_norm_() {}
    
    /**
     * 明文版本的K-Means（用于验证和基准测试）
     */
    struct ClusterResult {
        std::vector<std::vector<double>> centroids;
        std::vector<int> labels;
        double total_time;
        double assignment_time;
        double update_time;
        double normalize_time;
    };
    
    ClusterResult fit_plaintext(
        const std::vector<std::vector<double>>& vectors) {
        
        int n = vectors.size();
        int dim = vectors[0].size();
        
        ClusterResult result;
        result.assignment_time = 0;
        result.update_time = 0;
        result.normalize_time = 0;
        
        // 随机初始化质心
        result.centroids.resize(n_clusters_);
        std::random_device rd;
        std::mt19937 gen(rd());
        std::vector<int> indices(n);
        std::iota(indices.begin(), indices.end(), 0);
        std::shuffle(indices.begin(), indices.end(), gen);
        
        for (int c = 0; c < n_clusters_; ++c) {
            result.centroids[c] = vectors[indices[c]];
        }
        
        result.labels.resize(n);
        
        // 迭代
        for (int iter = 0; iter < max_iter_; ++iter) {
            // 软分配
            std::vector<std::vector<double>> weights(n);
            
            #pragma omp parallel for
            for (int i = 0; i < n; ++i) {
                std::vector<double> distances(n_clusters_);
                for (int c = 0; c < n_clusters_; ++c) {
                    distances[c] = euclidean_distance(vectors[i], result.centroids[c]);
                }
                weights[i] = softmin_.compute_plaintext(distances);
            }
            
            // 更新质心
            std::vector<std::vector<double>> new_centroids(n_clusters_, 
                                                           std::vector<double>(dim, 0.0));
            std::vector<double> weight_sums(n_clusters_, 0.0);
            
            for (int i = 0; i < n; ++i) {
                for (int c = 0; c < n_clusters_; ++c) {
                    weight_sums[c] += weights[i][c];
                    for (int d = 0; d < dim; ++d) {
                        new_centroids[c][d] += weights[i][c] * vectors[i][d];
                    }
                }
            }
            
            for (int c = 0; c < n_clusters_; ++c) {
                if (weight_sums[c] > 1e-10) {
                    for (int d = 0; d < dim; ++d) {
                        new_centroids[c][d] /= weight_sums[c];
                    }
                }
                // 归一化
                result.centroids[c] = homo_norm_.normalize_plaintext(new_centroids[c]);
            }
        }
        
        // 硬分配得到最终标签
        #pragma omp parallel for
        for (int i = 0; i < n; ++i) {
            double min_dist = std::numeric_limits<double>::max();
            for (int c = 0; c < n_clusters_; ++c) {
                double dist = euclidean_distance(vectors[i], result.centroids[c]);
                if (dist < min_dist) {
                    min_dist = dist;
                    result.labels[i] = c;
                }
            }
        }
        
        return result;
    }
    
private:
    double euclidean_distance(const std::vector<double>& a, 
                               const std::vector<double>& b) const {
        double sum = 0.0;
        for (size_t i = 0; i < a.size(); ++i) {
            double diff = a[i] - b[i];
            sum += diff * diff;
        }
        return std::sqrt(sum);
    }
    
    int n_clusters_;
    int max_iter_;
    PolySoftmin softmin_;
    HomoNorm homo_norm_;
};

} // namespace pprag
