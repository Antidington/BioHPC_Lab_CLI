#include <cuda_runtime.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

#include <thrust/copy.h>
#include <thrust/device_vector.h>
#include <thrust/iterator/constant_iterator.h>
#include <thrust/reduce.h>
#include <thrust/sort.h>

#include "bhlab/kmer.hpp"
#include "bhlab/layout.hpp"

namespace bhlab {
namespace {

__device__ uint64_t reverse_complement_device(uint64_t kmer, int k) {
  uint64_t out = 0;
  for (int i = 0; i < k; ++i) {
    const uint64_t base = kmer & 0x3ULL;
    out = (out << 2) | (3ULL - base);
    kmer >>= 2;
  }
  return out;
}

__global__ void emit_kmers(const uint64_t* packed, const uint32_t* offsets,
                           const uint32_t* lengths, int reads, int k, uint64_t* out,
                           unsigned int* out_count) {
  const int read = blockIdx.x * blockDim.x + threadIdx.x;
  if (read >= reads) return;
  const uint32_t length = lengths[read];
  if (length < static_cast<uint32_t>(k)) return;
  const std::size_t offset = offsets[read];
  const uint64_t mask = (1ULL << (2 * k)) - 1ULL;
  uint64_t forward = 0;
  for (uint32_t pos = 0; pos < length; ++pos) {
    const uint64_t word = packed[offset + pos / 32];
    const uint8_t base = static_cast<uint8_t>((word >> (2 * (pos % 32))) & 0x3ULL);
    forward = ((forward << 2) | base) & mask;
    if (pos + 1 >= static_cast<uint32_t>(k)) {
      const uint64_t reverse = reverse_complement_device(forward, k);
      const uint64_t canonical = forward < reverse ? forward : reverse;
      const unsigned int slot = atomicAdd(out_count, 1U);
      out[slot] = canonical;
    }
  }
}

}  // namespace

std::vector<KmerCount> count_kmers_gpu(const SeqBatch& input, int k) {
  if (k <= 0 || k > 31) throw std::runtime_error("k must be between 1 and 31");
  const SeqBatch batch = input.layout == Layout::SoA2 ? input : convert_layout(input, Layout::SoA2);
  if (batch.size() == 0) return {};

  std::vector<uint64_t> flat;
  std::vector<uint32_t> offsets;
  std::vector<uint32_t> lengths;
  offsets.reserve(batch.size());
  lengths.reserve(batch.size());
  for (std::size_t i = 0; i < batch.size(); ++i) {
    offsets.push_back(static_cast<uint32_t>(flat.size()));
    lengths.push_back(batch.lengths[i]);
    flat.insert(flat.end(), batch.packed[i].begin(), batch.packed[i].end());
  }
  const std::size_t max_kmers = batch.total_bases();
  if (max_kmers == 0) return {};

  uint64_t* d_packed = nullptr;
  uint32_t* d_offsets = nullptr;
  uint32_t* d_lengths = nullptr;
  uint64_t* d_out = nullptr;
  unsigned int* d_count = nullptr;
  cudaMalloc(&d_packed, flat.size() * sizeof(uint64_t));
  cudaMalloc(&d_offsets, offsets.size() * sizeof(uint32_t));
  cudaMalloc(&d_lengths, lengths.size() * sizeof(uint32_t));
  cudaMalloc(&d_out, max_kmers * sizeof(uint64_t));
  cudaMalloc(&d_count, sizeof(unsigned int));
  cudaMemcpy(d_packed, flat.data(), flat.size() * sizeof(uint64_t), cudaMemcpyHostToDevice);
  cudaMemcpy(d_offsets, offsets.data(), offsets.size() * sizeof(uint32_t), cudaMemcpyHostToDevice);
  cudaMemcpy(d_lengths, lengths.data(), lengths.size() * sizeof(uint32_t), cudaMemcpyHostToDevice);
  cudaMemset(d_count, 0, sizeof(unsigned int));

  const int threads = 128;
  const int blocks = static_cast<int>((batch.size() + threads - 1) / threads);
  emit_kmers<<<blocks, threads>>>(d_packed, d_offsets, d_lengths,
                                  static_cast<int>(batch.size()), k, d_out, d_count);

  unsigned int count = 0;
  cudaMemcpy(&count, d_count, sizeof(unsigned int), cudaMemcpyDeviceToHost);
  std::vector<KmerCount> result;
  if (count > 0) {
    thrust::device_vector<uint64_t> keys(d_out, d_out + count);
    thrust::sort(keys.begin(), keys.end());
    thrust::device_vector<uint64_t> unique_keys(count);
    thrust::device_vector<uint32_t> unique_counts(count);
    const auto end = thrust::reduce_by_key(
        keys.begin(), keys.end(), thrust::constant_iterator<uint32_t>(1), unique_keys.begin(),
        unique_counts.begin());
    const std::size_t unique = static_cast<std::size_t>(end.first - unique_keys.begin());
    std::vector<uint64_t> host_keys(unique);
    std::vector<uint32_t> host_counts(unique);
    thrust::copy(unique_keys.begin(), unique_keys.begin() + unique, host_keys.begin());
    thrust::copy(unique_counts.begin(), unique_counts.begin() + unique, host_counts.begin());
    result.reserve(unique);
    for (std::size_t i = 0; i < unique; ++i) result.push_back({host_keys[i], host_counts[i]});
  }

  cudaFree(d_packed);
  cudaFree(d_offsets);
  cudaFree(d_lengths);
  cudaFree(d_out);
  cudaFree(d_count);
  return result;
}

}  // namespace bhlab
