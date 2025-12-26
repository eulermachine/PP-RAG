/**
 * seal_utils.cpp
 * CKKS基础操作封装 - 完整实现
 * 
 * 提供加密、解密、同态运算接口
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
 * CKKS加密上下文管理器
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
    
    // ==================== 基础信息 ====================
    
    size_t slot_count() const {
        #ifdef USE_SEAL
        return encoder_->slot_count();
        #else
        return poly_degree_ / 2;
        #endif
    }
    
    double scale() const { return scale_; }
    size_t poly_degree() const { return poly_degree_; }
    
    // ==================== 加密/解密 ====================
    
    #ifdef USE_SEAL
    /**
     * 加密单个向量
     */
    Ciphertext encrypt_vector(const std::vector<double>& vec) {
        Plaintext plain;
        encoder_->encode(vec, scale_, plain);
        
        Ciphertext encrypted;
        encryptor_->encrypt(plain, encrypted);
        return encrypted;
    }
    
    /**
     * 批量加密多个向量（每个向量打包到一个密文）
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
     * 解密到向量
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
    
    // ==================== 同态运算 ====================
    
    /**
     * 同态加法
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
     * 同态乘法（需要relinearize和rescale）
     */
    Ciphertext he_multiply(const Ciphertext& ct1, const Ciphertext& ct2) {
        Ciphertext result;
        evaluator_->multiply(ct1, ct2, result);
        evaluator_->relinearize_inplace(result, relin_keys_);
        evaluator_->rescale_to_next_inplace(result);
        return result;
    }
    
    /**
     * 明文常数乘法
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
     * 同态减法
     */
    Ciphertext he_subtract(const Ciphertext& ct1, const Ciphertext& ct2) {
        Ciphertext result;
        evaluator_->sub(ct1, ct2, result);
        return result;
    }
    
    /**
     * 同态平方
     */
    Ciphertext he_square(const Ciphertext& ct) {
        Ciphertext result;
        evaluator_->square(ct, result);
        evaluator_->relinearize_inplace(result, relin_keys_);
        evaluator_->rescale_to_next_inplace(result);
        return result;
    }
    
    /**
     * 向量旋转
     */
    Ciphertext he_rotate(const Ciphertext& ct, int steps) {
        Ciphertext result;
        evaluator_->rotate_vector(ct, steps, galois_keys_, result);
        return result;
    }
    
    // ==================== 复合运算 ====================
    
    /**
     * 同态内积计算
     * 使用 multiply + rotate-and-sum 模式
     */
    Ciphertext he_inner_product(const Ciphertext& ct1, const Ciphertext& ct2) {
        // 元素级乘法
        Ciphertext result = he_multiply(ct1, ct2);
        
        // Rotate and sum to get inner product
        size_t slots = slot_count();
        for (size_t i = 1; i < slots; i *= 2) {
            Ciphertext rotated = he_rotate(result, static_cast<int>(i));
            // 对齐scale进行加法
            match_scale_and_add_inplace(result, rotated);
        }
        
        return result;
    }
    
    /**
     * 计算L2距离平方: ||a - b||^2
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
    
    // ==================== 辅助函数 ====================
    
    /**
     * 匹配scale后进行加法
     */
    void match_scale_and_add_inplace(Ciphertext& ct1, Ciphertext& ct2) {
        // 匹配parms_id
        if (ct1.parms_id() != ct2.parms_id()) {
            // 找到更低的level
            auto ctx_data1 = context_->get_context_data(ct1.parms_id());
            auto ctx_data2 = context_->get_context_data(ct2.parms_id());
            
            if (ctx_data1->chain_index() > ctx_data2->chain_index()) {
                evaluator_->mod_switch_to_inplace(ct1, ct2.parms_id());
            } else {
                evaluator_->mod_switch_to_inplace(ct2, ct1.parms_id());
            }
        }
        
        // 匹配scale
        ct1.scale() = scale_;
        ct2.scale() = scale_;
        
        evaluator_->add_inplace(ct1, ct2);
    }
    
    /**
     * 获取密文噪声预算（用于调试）
     */
    int noise_budget(const Ciphertext& ct) {
        return decryptor_->invariant_noise_budget(ct);
    }
    
    // 公开访问器（供其他模块使用）
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
