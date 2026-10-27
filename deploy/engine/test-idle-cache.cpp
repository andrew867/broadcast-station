#include "idle_cache.h"
#include <atomic>
#include <cassert>
#include <memory>
#include <thread>
using caspar::accelerator::ogl::idle_cache;
int main() {
    using value = std::shared_ptr<int>;
    idle_cache<int, value> pool(100);
    pool.put(1, std::make_shared<int>(1), 40);
    pool.put(2, std::make_shared<int>(2), 40);
    auto active = pool.take(1);
    assert(active && *active == 1);
    pool.put(1, active, 40);
    auto retired = pool.put(3, std::make_shared<int>(3), 50);
    assert(retired.size() == 1 && *retired[0] == 2);
    assert(!pool.take(2) && pool.status().bytes == 90);
    assert(*active == 1); // Cache eviction never invalidates an active owner.
    assert(pool.put(9, std::make_shared<int>(9), 101).size() == 1);
    pool.clear();
    assert(pool.status().bytes == 0 && pool.status().groups.empty());

    // Reproduce hundreds of one-off ticker sizes, then admit the UHD buffers.
    idle_cache<int, value> sizes(384);
    for (int i=0; i<1000; ++i) sizes.put(i, std::make_shared<int>(i), 3);
    sizes.put(4000, std::make_shared<int>(4000), 32);
    auto hot = sizes.take(4000);
    assert(hot && *hot == 4000 && sizes.status().bytes <= 384);
    std::vector<std::thread> threads;
    for (int t=0; t<8; ++t) threads.emplace_back([&,t] {
        for (int i=0; i<10000; ++i) {
            auto key=(i+t)%17; auto v=sizes.take(key);
            if (!v) v=std::make_shared<int>(key);
            auto unused=sizes.put(key,std::move(v),7);
            assert(sizes.status().bytes <= 384);
            if (i%1000==0) sizes.clear();
        }
    });
    for (auto& t:threads) t.join();
    sizes.clear();
    assert(sizes.status().bytes == 0);
}
