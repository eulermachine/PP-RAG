/**
 * bench_wrapper2.cpp
 * Python Bindings for Real CKKS Components - Variant 2
 * (Hybrid with Partial Client Decryption)
 */

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <chrono>

#include "seal_utils.cpp"
#include "poly_softmin.cpp"
#include "secure_hnsw.cpp"
#include "secure_hnsw2.cpp"

namespace py = pybind11;
using namespace pprag;

// Timer helper
class Timer {
public:
    void start() { start_ = std::chrono::high_resolution_clock::now(); }
    double elapsed() {
        auto end = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double>(end - start_).count();
    }
private:
    std::chrono::time_point<std::chrono::high_resolution_clock> start_;
};

// Numpy to Vector helper
std::vector<double> numpy_to_vector(py::array_t<double> arr) {
    auto buf = arr.request();
    double* ptr = static_cast<double*>(buf.ptr);
    return std::vector<double>(ptr, ptr + buf.size);
}

// Numpy to Matrix helper
std::vector<std::vector<double>> numpy_to_matrix(py::array_t<double> arr) {
    auto buf = arr.request();
    double* ptr = static_cast<double*>(buf.ptr);
    int rows = buf.shape[0];
    int cols = buf.shape[1];
    
    std::vector<std::vector<double>> result(rows);
    for (int i = 0; i < rows; ++i) {
        result[i].assign(ptr + i * cols, ptr + (i + 1) * cols);
    }
    return result;
}

PYBIND11_MODULE(pprag_core2, m) {
    m.doc() = "PP-RAG HE Core Components - Variant 2 (Real CKKS with Client-Aided Decryption)";
    
    // Note: We don't redefine Ciphertext to avoid conflicts with pprag_core
    // Instead, we only define the new SecureHNSWEncrypted2 class
    // The CKKSContext is expected to be imported from pprag_core
    
    // Bind SecureHNSWEncrypted2 (variant 2 with client-aided decryption)
    py::class_<SecureHNSWEncrypted2>(m, "SecureHNSWEncrypted2")
        .def(py::init<CKKSContext&, int, int, int>(),
             py::arg("ctx"),
             py::arg("M") = 16,
             py::arg("ef_construction") = 200,
             py::arg("ef_search") = 100)
        .def("add_encrypted_node", &SecureHNSWEncrypted2::add_encrypted_node)
        .def("search", [](SecureHNSWEncrypted2& self, Ciphertext& query, int k) {
            auto results = self.search(query, k);
            return py::array_t<int>(results.size(), results.data());
        })
        .def("get_communication_bytes", &SecureHNSWEncrypted2::get_communication_bytes)
        .def("reset_communication_counter", &SecureHNSWEncrypted2::reset_communication_counter);
}
