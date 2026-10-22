#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "bhlab/types.hpp"

namespace bhlab {

SeqBatch load_fastx(const std::string& path, Layout layout, std::size_t max_reads = 0);
SeqBatch convert_layout(const SeqBatch& batch, Layout target);
Layout parse_layout(const std::string& value);
std::string layout_name(Layout layout);
uint8_t base_at(const SeqBatch& batch, std::size_t read_index, std::size_t pos);
uint64_t pack_kmer(const SeqBatch& batch, std::size_t read_index, std::size_t pos, int k);
uint64_t reverse_complement(uint64_t kmer, int k);
uint64_t canonical_kmer(const SeqBatch& batch, std::size_t read_index, std::size_t pos, int k);
std::string kmer_string(uint64_t kmer, int k);
void write_counts_tsv(const std::string& path, const std::vector<KmerCount>& counts, int k);
void write_minimizers_tsv(const std::string& path, const std::vector<Minimizer>& mins, int k);

}  // namespace bhlab
