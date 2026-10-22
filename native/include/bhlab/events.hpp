#pragma once

#include <fstream>
#include <map>
#include <string>

namespace bhlab {

class EventLogger {
 public:
  EventLogger(const std::string& path, const std::string& job_id);
  void emit(const std::string& event, const std::string& level, const std::string& message,
            const std::map<std::string, std::string>& params = {});
  bool ok() const { return out_.good(); }

 private:
  std::ofstream out_;
  std::string job_id_;
  std::string host_;
};

std::string iso8601_now();
std::string hostname();

}  // namespace bhlab
