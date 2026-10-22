#pragma once

#include <vector>

#include "bhlab/types.hpp"

namespace bhlab {

std::vector<KmerCount> count_kmers(const SeqBatch& batch, int k, Device device, int threads);
std::vector<KmerCount> count_kmers_cpu(const SeqBatch& batch, int k, int threads);
#ifdef BHLAB_HAVE_CUDA
std::vector<KmerCount> count_kmers_gpu(const SeqBatch& batch, int k);
#endif

}  // namespace bhlab
