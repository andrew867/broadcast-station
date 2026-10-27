#pragma once
#include <cstddef>
#include <list>
#include <map>
#include <mutex>
#include <utility>
#include <vector>

namespace caspar { namespace accelerator { namespace ogl {
// Only idle objects enter this cache. Evicted values are returned to the
// caller so GPU destruction can happen on the GL thread, outside the lock.
template <class Key, class Value> class idle_cache {
    struct entry { Key key; Value value; std::size_t bytes; };
    std::size_t budget_, bytes_ = 0, evictions_ = 0;
    std::list<entry> entries_;
    mutable std::mutex mutex_;
public:
    explicit idle_cache(std::size_t budget) : budget_(budget) {}
    Value take(const Key& key) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto it = entries_.end(); it != entries_.begin();) {
            --it;
            if (it->key == key) {
                auto result = std::move(it->value);
                bytes_ -= it->bytes;
                entries_.erase(it);
                return result;
            }
        }
        return {};
    }
    std::vector<Value> put(Key key, Value value, std::size_t bytes) {
        std::vector<Value> retired;
        std::lock_guard<std::mutex> lock(mutex_);
        if (bytes > budget_) {
            retired.push_back(std::move(value));
            return retired;
        }
        // Admit the newly used size by evicting the oldest idle objects.
        while (bytes_ > budget_ - bytes) {
            bytes_ -= entries_.front().bytes;
            retired.push_back(std::move(entries_.front().value));
            entries_.pop_front();
            ++evictions_;
        }
        entries_.push_back({std::move(key), std::move(value), bytes});
        bytes_ += bytes;
        return retired;
    }
    std::vector<Value> clear() {
        std::vector<Value> retired;
        std::lock_guard<std::mutex> lock(mutex_);
        retired.reserve(entries_.size());
        for (auto& item : entries_) retired.push_back(std::move(item.value));
        entries_.clear(); bytes_ = 0;
        return retired;
    }
    struct snapshot {
        std::size_t bytes, evictions;
        std::map<Key, std::pair<std::size_t, std::size_t>> groups;
    };
    snapshot status() const {
        std::lock_guard<std::mutex> lock(mutex_);
        snapshot result{bytes_, evictions_, {}};
        for (const auto& item : entries_) {
            auto& group = result.groups[item.key];
            ++group.first; group.second += item.bytes;
        }
        return result;
    }
};
}}}
