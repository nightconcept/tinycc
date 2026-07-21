/* Sieve of Eratosthenes, repeated -- array-heavy integer workload. */
#include <stdio.h>

#define LIMIT 1000000
static char is_composite[LIMIT];

int main(void) {
    int reps, r;
    long total_primes = 0;

    for (reps = 0; reps < 80; reps++) {
        int i, j;
        for (i = 0; i < LIMIT; i++) is_composite[i] = 0;
        long count = 0;
        for (i = 2; i < LIMIT; i++) {
            if (!is_composite[i]) {
                count++;
                for (j = i + i; j < LIMIT; j += i) is_composite[j] = 1;
            }
        }
        total_primes += count;
    }
    printf("sieve total_primes=%ld\n", total_primes);
    return 0;
}
