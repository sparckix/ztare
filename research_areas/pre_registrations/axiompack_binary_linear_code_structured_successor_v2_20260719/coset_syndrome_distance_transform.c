/* Bounded resource probe for a min-plus Hamming transform.

   The input file contains

       <syndrome_bits> <center_generator_count>
       <hex center generator 0>
       ...

   If the center generators are the parity portions of [I | A], the initial
   value at XOR_i u_i A_i is wt(u).  One min-plus butterfly per syndrome bit
   then computes

       d(s) = min_u (wt(u) + wt(s XOR uA)),

   which is the exact coset-leader weight on the probed quotient.  This source
   is deliberately capped below the 31-bit campaign instance.  It measures
   the order and resource curve only; it cannot emit the campaign certificate.
*/

#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

enum {
    DISTANCE_INF = 63,
    MAX_THREADS = 64,
    MAX_CENTER_GENERATORS = 63,
    MAX_PROBE_SYNDROME_BITS = 26
};

typedef struct {
    uint8_t *distance;
    uint64_t state_count;
    unsigned bit;
    unsigned thread_index;
    unsigned thread_count;
} ButterflyTask;

static void fail(const char *message) {
    fprintf(stderr, "%s: %s\n", message, strerror(errno));
    exit(2);
}

static uint64_t elapsed_ms(struct timespec start, struct timespec end) {
    uint64_t seconds = (uint64_t)(end.tv_sec - start.tv_sec);
    int64_t nanos = end.tv_nsec - start.tv_nsec;
    if (nanos < 0) {
        seconds -= 1;
        nanos += 1000000000LL;
    }
    return seconds * 1000ULL + (uint64_t)nanos / 1000000ULL;
}

static inline void update_pair(uint8_t *restrict left, uint8_t *restrict right) {
    uint8_t a = *left;
    uint8_t b = *right;
    uint8_t through_b = (uint8_t)(b + 1U);
    uint8_t through_a = (uint8_t)(a + 1U);
    *left = a < through_b ? a : through_b;
    *right = b < through_a ? b : through_a;
}

static void *butterfly_worker(void *raw) {
    ButterflyTask *task = (ButterflyTask *)raw;
    uint64_t half = 1ULL << task->bit;
    uint64_t block_size = half << 1U;
    uint64_t block_count = task->state_count / block_size;
    unsigned t = task->thread_index;
    unsigned threads = task->thread_count;

    if (block_count >= threads) {
        for (uint64_t block = t; block < block_count; block += threads) {
            uint64_t base = block * block_size;
            uint8_t *restrict left = task->distance + base;
            uint8_t *restrict right = left + half;
            for (uint64_t offset = 0; offset < half; ++offset) {
                update_pair(left + offset, right + offset);
            }
        }
    } else {
        for (uint64_t block = 0; block < block_count; ++block) {
            uint64_t begin = (half * t) / threads;
            uint64_t end = (half * (t + 1U)) / threads;
            uint64_t base = block * block_size;
            uint8_t *restrict left = task->distance + base;
            uint8_t *restrict right = left + half;
            for (uint64_t offset = begin; offset < end; ++offset) {
                update_pair(left + offset, right + offset);
            }
        }
    }
    return NULL;
}

static void run_butterfly(
    uint8_t *distance,
    uint64_t state_count,
    unsigned bit,
    unsigned thread_count
) {
    pthread_t threads[MAX_THREADS];
    ButterflyTask tasks[MAX_THREADS];
    for (unsigned t = 0; t < thread_count; ++t) {
        tasks[t] = (ButterflyTask){
            .distance = distance,
            .state_count = state_count,
            .bit = bit,
            .thread_index = t,
            .thread_count = thread_count,
        };
        int rc = pthread_create(&threads[t], NULL, butterfly_worker, &tasks[t]);
        if (rc != 0) {
            errno = rc;
            fail("pthread_create");
        }
    }
    for (unsigned t = 0; t < thread_count; ++t) {
        int rc = pthread_join(threads[t], NULL);
        if (rc != 0) {
            errno = rc;
            fail("pthread_join");
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s MASK_FILE TABLE_FILE THREADS\n", argv[0]);
        return 2;
    }
    char *thread_end = NULL;
    unsigned long parsed_threads = strtoul(argv[3], &thread_end, 10);
    if (*argv[3] == '\0' || *thread_end != '\0' || parsed_threads < 1 ||
        parsed_threads > MAX_THREADS) {
        fprintf(stderr, "thread count must lie in [1,%d]\n", MAX_THREADS);
        return 2;
    }
    unsigned thread_count = (unsigned)parsed_threads;

    FILE *input = fopen(argv[1], "r");
    if (input == NULL) {
        fail("open mask file");
    }
    unsigned syndrome_bits = 0;
    unsigned generator_count = 0;
    if (fscanf(input, "%u %u", &syndrome_bits, &generator_count) != 2 ||
        syndrome_bits < 1 || syndrome_bits > MAX_PROBE_SYNDROME_BITS ||
        generator_count > MAX_CENTER_GENERATORS) {
        fprintf(stderr, "invalid mask-file header\n");
        return 2;
    }
    uint64_t masks[MAX_CENTER_GENERATORS];
    uint64_t state_count = 1ULL << syndrome_bits;
    for (unsigned index = 0; index < generator_count; ++index) {
        if (fscanf(input, "%" SCNx64, &masks[index]) != 1 ||
            masks[index] >= state_count) {
            fprintf(stderr, "invalid center generator at index %u\n", index);
            return 2;
        }
    }
    char trailing[2];
    if (fscanf(input, "%1s", trailing) == 1) {
        fprintf(stderr, "mask file has trailing data\n");
        return 2;
    }
    if (fclose(input) != 0) {
        fail("close mask file");
    }

    int table_fd = open(argv[2], O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (table_fd < 0) {
        fail("open distance table");
    }
    if (ftruncate(table_fd, (off_t)state_count) != 0) {
        fail("size distance table");
    }
    uint8_t *distance = mmap(
        NULL,
        (size_t)state_count,
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        table_fd,
        0
    );
    if (distance == MAP_FAILED) {
        fail("map distance table");
    }

    struct timespec started;
    struct timespec transformed;
    struct timespec finished;
    if (clock_gettime(CLOCK_MONOTONIC, &started) != 0) {
        fail("clock_gettime");
    }
    memset(distance, DISTANCE_INF, (size_t)state_count);
    distance[0] = 0;
    uint64_t center = 0;
    uint64_t previous_gray = 0;
    uint64_t center_count = 1ULL << generator_count;
    for (uint64_t step = 1; step < center_count; ++step) {
        uint64_t gray = step ^ (step >> 1U);
        uint64_t changed = gray ^ previous_gray;
        unsigned changed_index = (unsigned)__builtin_ctzll(changed);
        center ^= masks[changed_index];
        uint8_t weight = (uint8_t)__builtin_popcountll(gray);
        if (weight < distance[center]) {
            distance[center] = weight;
        }
        previous_gray = gray;
    }

    for (unsigned bit = 0; bit < syndrome_bits; ++bit) {
        run_butterfly(distance, state_count, bit, thread_count);
    }
    if (clock_gettime(CLOCK_MONOTONIC, &transformed) != 0) {
        fail("clock_gettime");
    }

    uint64_t histogram[DISTANCE_INF + 1U];
    memset(histogram, 0, sizeof(histogram));
    uint8_t maximum = 0;
    uint64_t first_maximum = 0;
    for (uint64_t syndrome = 0; syndrome < state_count; ++syndrome) {
        uint8_t value = distance[syndrome];
        if (value > DISTANCE_INF) {
            fprintf(stderr, "distance table contains an invalid value\n");
            return 2;
        }
        histogram[value] += 1;
        if (value > maximum) {
            maximum = value;
            first_maximum = syndrome;
        }
    }
    if (msync(distance, (size_t)state_count, MS_SYNC) != 0) {
        fail("sync distance table");
    }
    if (munmap(distance, (size_t)state_count) != 0) {
        fail("unmap distance table");
    }
    if (close(table_fd) != 0) {
        fail("close distance table");
    }
    if (clock_gettime(CLOCK_MONOTONIC, &finished) != 0) {
        fail("clock_gettime");
    }

    printf("{\"schema\":\"axiompack.binary_syndrome_distance_transform_resource_probe.v1\",");
    printf("\"syndrome_bits\":%u,", syndrome_bits);
    printf("\"center_generator_count\":%u,", generator_count);
    printf("\"initial_center_count\":%" PRIu64 ",", center_count);
    printf("\"state_count\":%" PRIu64 ",", state_count);
    printf("\"thread_count\":%u,", thread_count);
    printf("\"transform_elapsed_ms\":%" PRIu64 ",", elapsed_ms(started, transformed));
    printf("\"total_elapsed_ms\":%" PRIu64 ",", elapsed_ms(started, finished));
    printf("\"maximum_distance\":%u,", (unsigned)maximum);
    printf("\"first_maximum_syndrome\":\"0x%08" PRIx64 "\",", first_maximum);
    printf("\"histogram\":[");
    for (unsigned value = 0; value <= DISTANCE_INF; ++value) {
        if (value != 0) {
            putchar(',');
        }
        printf("%" PRIu64, histogram[value]);
    }
    printf("]}\n");
    return 0;
}
