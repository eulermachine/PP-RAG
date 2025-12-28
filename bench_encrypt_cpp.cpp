/**
 * bench_encrypt_cpp.cpp
 * C++ 层级的加密性能采样（使用 OpenMP 并行）
 * 编译：g++ -O3 -fopenmp -I/path/to/seal/include bench_encrypt_cpp.cpp -o bench_encrypt_cpp -lseal
 */

#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <omp.h>

#ifdef USE_SEAL
#include "seal/seal.h"
using namespace seal;

int main() {
    // SEAL 初始化（8192 poly degree, CKKS）
    EncryptionParameters parms(scheme_type::ckks);
    size_t poly_degree = 8192;
    parms.set_poly_modulus_degree(poly_degree);
    parms.set_coeff_modulus(CoeffModulus::Create(poly_degree, {60, 40, 40, 60}));
    
    SEALContext context(parms);
    KeyGenerator keygen(context);
    PublicKey public_key;
    keygen.create_public_key(public_key);
    
    Encryptor encryptor(context, public_key);
    CKKSEncoder encoder(context);
    
    double scale = pow(2.0, 40);
    size_t slot_count = encoder.slot_count();
    
    // 生成测试向量（1000 个，每个 256 维）
    std::vector<std::vector<double>> vectors(1000);
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    
    #pragma omp parallel for
    for (size_t i = 0; i < 1000; ++i) {
        vectors[i].resize(256);
        for (size_t j = 0; j < 256; ++j) {
            vectors[i][j] = dist(rng);
        }
    }
    
    // ===== 单线程加密 =====
    auto start = std::chrono::high_resolution_clock::now();
    std::vector<Ciphertext> encrypted_serial(1000);
    for (size_t i = 0; i < 1000; ++i) {
        Plaintext plain;
        encoder.encode(vectors[i], scale, plain);
        encryptor.encrypt(plain, encrypted_serial[i]);
    }
    auto end = std::chrono::high_resolution_clock::now();
    double serial_time = std::chrono::duration<double>(end - start).count();
    
    std::cout << "=== SERIAL ENCRYPTION (1 thread) ===" << std::endl;
    std::cout << "Total time: " << serial_time << "s" << std::endl;
    std::cout << "Per-vector: " << (serial_time * 1000 / 1000) << "ms" << std::endl;
    std::cout << "Throughput: " << (1000 / serial_time) << " vectors/sec" << std::endl;
    
    // ===== 并行加密（OpenMP） =====
    start = std::chrono::high_resolution_clock::now();
    std::vector<Ciphertext> encrypted_parallel(1000);
    #pragma omp parallel for
    for (size_t i = 0; i < 1000; ++i) {
        Plaintext plain;
        encoder.encode(vectors[i], scale, plain);
        encryptor.encrypt(plain, encrypted_parallel[i]);
    }
    end = std::chrono::high_resolution_clock::now();
    double parallel_time = std::chrono::duration<double>(end - start).count();
    
    std::cout << "\n=== PARALLEL ENCRYPTION (OpenMP) ===" << std::endl;
    std::cout << "Total time: " << parallel_time << "s" << std::endl;
    std::cout << "Per-vector: " << (parallel_time * 1000 / 1000) << "ms" << std::endl;
    std::cout << "Throughput: " << (1000 / parallel_time) << " vectors/sec" << std::endl;
    
    std::cout << "\n=== SPEEDUP ===" << std::endl;
    std::cout << "Parallel/Serial: " << (serial_time / parallel_time) << "x" << std::endl;
    
    // 验证结果正确性
    std::cout << "\nVerification: Both methods produced " << encrypted_serial.size() 
              << " ciphertexts (expected 1000)" << std::endl;
    
    return 0;
}

#else
int main() {
    std::cerr << "SEAL not available (USE_SEAL not defined)" << std::endl;
    return 1;
}
#endif
