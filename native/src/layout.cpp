#include "bhlab/layout.hpp"

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

#ifdef BHLAB_HAVE_ZLIB
#include <zlib.h>
#endif

namespace bhlab {
namespace {

class LineReader {
 public:
  explicit LineReader(const std::string& path) : path_(path) {
    const bool gz = path.size() > 3 && path.substr(path.size() - 3) == ".gz";
    if (gz) {
#ifdef BHLAB_HAVE_ZLIB
      file_ = gzopen(path.c_str(), "rb");
      if (file_ == nullptr) throw std::runtime_error("cannot open " + path);
      gz_ = true;
#else
      throw std::runtime_error("gzip input requires zlib, rebuild with BHLAB_HAVE_ZLIB");
#endif
    } else {
      in_.open(path);
      if (!in_) throw std::runtime_error("cannot open " + path);
    }
  }

  ~LineReader() {
#ifdef BHLAB_HAVE_ZLIB
    if (gz_ && file_ != nullptr) gzclose(file_);
#endif
  }

  bool getline(std::string& line) {
#ifdef BHLAB_HAVE_ZLIB
    if (gz_) {
      char buffer[1 << 16];
      line.clear();
      while (gzgets(file_, buffer, sizeof(buffer)) != nullptr) {
        line += buffer;
        if (!line.empty() && line.back() == '\n') {
          line.pop_back();
          if (!line.empty() && line.back() == '\r') line.pop_back();
          return true;
        }
      }
      return !line.empty();
    }
#endif
    if (!std::getline(in_, line)) return false;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    return true;
  }

 private:
  std::string path_;
  bool gz_ = false;
#ifdef BHLAB_HAVE_ZLIB
  gzFile file_ = nullptr;
#endif
  std::ifstream in_;
};

bool is_acgt(const std::string& seq) {
  for (char c : seq) {
    const char u = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    if (u != 'A' && u != 'C' && u != 'G' && u != 'T') return false;
  }
  return true;
}

std::vector<uint64_t> pack_sequence(const std::string& seq) {
  std::vector<uint64_t> words((seq.size() + 31) / 32, 0);
  for (std::size_t i = 0; i < seq.size(); ++i) {
    uint8_t code = 0;
    switch (static_cast<char>(std::toupper(static_cast<unsigned char>(seq[i])))) {
      case 'A': code = 0; break;
      case 'C': code = 1; break;
      case 'G': code = 2; break;
      case 'T': code = 3; break;
      default: throw std::runtime_error("non ACGT base reached pack_sequence");
    }
    words[i / 32] |= (static_cast<uint64_t>(code) << (2 * (i % 32)));
  }
  return words;
}

std::string unpack_sequence(const std::vector<uint64_t>& words, std::size_t length) {
  static const char bases[] = "ACGT";
  std::string seq(length, 'A');
  for (std::size_t i = 0; i < length; ++i) {
    const uint64_t code = (words[i / 32] >> (2 * (i % 32))) & 0x3ULL;
    seq[i] = bases[code];
  }
  return seq;
}

}  // namespace

std::size_t SeqBatch::total_bases() const {
  std::size_t total = 0;
  for (uint32_t length : lengths) total += length;
  return total;
}

SeqBatch load_fastx(const std::string& path, Layout layout, std::size_t max_reads) {
  LineReader reader(path);
  SeqBatch batch;
  batch.layout = layout;

  std::string line;
  if (!reader.getline(line)) return batch;

  if (!line.empty() && line[0] == '>') {
    std::string id = line.substr(1);
    std::string seq;
    while (reader.getline(line)) {
      if (!line.empty() && line[0] == '>') {
        if (!seq.empty()) {
          if (is_acgt(seq)) {
            batch.ids.push_back(id);
            batch.lengths.push_back(static_cast<uint32_t>(seq.size()));
            batch.seqs.push_back(seq);
          } else {
            ++batch.skipped_reads;
          }
          seq.clear();
        }
        if (max_reads != 0 && batch.size() >= max_reads) break;
        id = line.substr(1);
      } else {
        seq += line;
      }
    }
    if (max_reads == 0 || batch.size() < max_reads) {
      if (!seq.empty()) {
        if (is_acgt(seq)) {
          batch.ids.push_back(id);
          batch.lengths.push_back(static_cast<uint32_t>(seq.size()));
          batch.seqs.push_back(seq);
        } else {
          ++batch.skipped_reads;
        }
      }
    }
  } else if (!line.empty() && line[0] == '@') {
    do {
      const std::string id = line.substr(1);
      std::string seq;
      std::string plus;
      std::string qual;
      if (!reader.getline(seq) || !reader.getline(plus) || !reader.getline(qual)) break;
      if (is_acgt(seq)) {
        batch.ids.push_back(id);
        batch.lengths.push_back(static_cast<uint32_t>(seq.size()));
        batch.seqs.push_back(seq);
      } else {
        ++batch.skipped_reads;
      }
      if (max_reads != 0 && batch.size() >= max_reads) break;
    } while (reader.getline(line) && !line.empty() && line[0] == '@');
  } else {
    throw std::runtime_error("input must be FASTA or FASTQ: " + path);
  }

  if (layout == Layout::SoA2) {
    batch.packed.reserve(batch.ids.size());
    for (const std::string& seq : batch.seqs) batch.packed.push_back(pack_sequence(seq));
    batch.seqs.clear();
    batch.seqs.shrink_to_fit();
  }
  return batch;
}

SeqBatch convert_layout(const SeqBatch& batch, Layout target) {
  if (batch.layout == target) return batch;
  SeqBatch out;
  out.layout = target;
  out.ids = batch.ids;
  out.lengths = batch.lengths;
  out.skipped_reads = batch.skipped_reads;
  if (target == Layout::AoS8) {
    out.seqs.reserve(batch.size());
    for (std::size_t i = 0; i < batch.size(); ++i) {
      out.seqs.push_back(unpack_sequence(batch.packed[i], batch.lengths[i]));
    }
  } else {
    out.packed.reserve(batch.size());
    for (const std::string& seq : batch.seqs) out.packed.push_back(pack_sequence(seq));
  }
  return out;
}

Layout parse_layout(const std::string& value) {
  if (value == "aos8") return Layout::AoS8;
  if (value == "soa2") return Layout::SoA2;
  throw std::runtime_error("layout must be aos8 or soa2: " + value);
}

std::string layout_name(Layout layout) {
  return layout == Layout::AoS8 ? "aos8" : "soa2";
}

uint8_t base_at(const SeqBatch& batch, std::size_t read_index, std::size_t pos) {
  if (batch.layout == Layout::AoS8) {
    const char c = batch.seqs[read_index][pos];
    switch (c) {
      case 'A': return 0;
      case 'C': return 1;
      case 'G': return 2;
      case 'T': return 3;
      default: throw std::runtime_error("invalid base");
    }
  }
  const uint64_t word = batch.packed[read_index][pos / 32];
  return static_cast<uint8_t>((word >> (2 * (pos % 32))) & 0x3ULL);
}

uint64_t pack_kmer(const SeqBatch& batch, std::size_t read_index, std::size_t pos, int k) {
  uint64_t kmer = 0;
  for (int i = 0; i < k; ++i) {
    kmer = (kmer << 2) | base_at(batch, read_index, pos + static_cast<std::size_t>(i));
  }
  return kmer;
}

uint64_t reverse_complement(uint64_t kmer, int k) {
  uint64_t out = 0;
  for (int i = 0; i < k; ++i) {
    const uint64_t base = kmer & 0x3ULL;
    out = (out << 2) | (3ULL - base);
    kmer >>= 2;
  }
  return out;
}

uint64_t canonical_kmer(const SeqBatch& batch, std::size_t read_index, std::size_t pos, int k) {
  const uint64_t forward = pack_kmer(batch, read_index, pos, k);
  const uint64_t reverse = reverse_complement(forward, k);
  return std::min(forward, reverse);
}

std::string kmer_string(uint64_t kmer, int k) {
  static const char bases[] = "ACGT";
  std::string out(static_cast<std::size_t>(k), 'A');
  for (int i = k - 1; i >= 0; --i) {
    out[static_cast<std::size_t>(k - 1 - i)] = bases[(kmer >> (2 * i)) & 0x3ULL];
  }
  return out;
}

void write_counts_tsv(const std::string& path, const std::vector<KmerCount>& counts, int k) {
  const std::filesystem::path target(path);
  if (target.has_parent_path()) std::filesystem::create_directories(target.parent_path());
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write " + path);
  out << "kmer\tcount\n";
  for (const KmerCount& row : counts) out << kmer_string(row.kmer, k) << '\t' << row.count << '\n';
}

void write_minimizers_tsv(const std::string& path, const std::vector<Minimizer>& mins, int k) {
  const std::filesystem::path target(path);
  if (target.has_parent_path()) std::filesystem::create_directories(target.parent_path());
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write " + path);
  out << "read_id\tpos\tkmer\thash\n";
  for (const Minimizer& row : mins) {
    out << row.read_index << '\t' << row.pos << '\t' << kmer_string(row.hash, k) << '\t' << row.hash
        << '\n';
  }
}

}  // namespace bhlab
