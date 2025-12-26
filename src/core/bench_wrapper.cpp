/**
 * bench_wrapper.cpp
 * Python Bindings for Real CKKS Components
 */

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include <chrono>

#include "seal_utils.cpp"
#include "poly_softmin.cpp"
#include "secure_hnsw.cpp"

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

PYBIND11_MODULE(pprag_core, m) {
    m.doc() = "PP-RAG HE Core Components (Real CKKS)";
    
    // Bind SEAL Ciphertext (Opaque handle)
    py::class_<Ciphertext>(m, "Ciphertext")
        .def(py::init<>());

    // Bind CKKSContext
    py::class_<CKKSContext>(m, "CKKSContext")
        .def(py::init<size_t, double>(), 
             py::arg("poly_modulus_degree") = 8192, 
             py::arg("scale") = std::pow(2.0, 40))
        .def("encrypt_vector", [](CKKSContext& self, py::array_t<double> vec) {
            return self.encrypt_vector(numpy_to_vector(vec));
        })
        .def("decrypt_vector", [](CKKSContext& self, Ciphertext& ct) {
            auto vec = self.decrypt_vector(ct);
            return py::array_t<double>(vec.size(), vec.data());
        })
        .def("slot_count", &CKKSContext::slot_count);

    // Bind PolySoftmin
    py::class_<PolySoftmin>(m, "PolySoftmin")
        .def(py::init<int, double>(), py::arg("degree") = 4, py::arg("temperature") = 1.0)
        .def("compute_plaintext", [](PolySoftmin& self, py::array_t<double> dists) {
            auto vec = self.compute_plaintext(numpy_to_vector(dists));
            return py::array_t<double>(vec.size(), vec.data());
        });

    // Bind SecureHNSWEncrypted
    py::class_<SecureHNSWEncrypted>(m, "SecureHNSWEncrypted")
        .def(py::init<CKKSContext&, int, int, int>(),
             py::arg("ctx"),
             py::arg("M") = 16,
             py::arg("ef_construction") = 200,
             py::arg("ef_search") = 100)
        .def("add_encrypted_node", &SecureHNSWEncrypted::add_encrypted_node)
        .def("search", [](SecureHNSWEncrypted& self, Ciphertext& query, int k) {
            auto results = self.search(query, k);
            return py::array_t<int>(results.size(), results.data());
        });
}
