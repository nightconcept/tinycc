/* Quicksort over a large int array, repeated -- recursion + memory traffic. */
#include <stdio.h>

#define N 200000

static void swap(int *a, int *b) {
    int t = *a;
    *a = *b;
    *b = t;
}

static void quicksort(int *arr, int lo, int hi) {
    if (lo >= hi) return;
    {
        int pivot = arr[(lo + hi) / 2];
        int i = lo, j = hi;
        while (i <= j) {
            while (arr[i] < pivot) i++;
            while (arr[j] > pivot) j--;
            if (i <= j) {
                swap(&arr[i], &arr[j]);
                i++;
                j--;
            }
        }
        quicksort(arr, lo, j);
        quicksort(arr, i, hi);
    }
}

static unsigned long rng_state = 88172645463325252UL;

static unsigned long xorshift(void) {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return rng_state;
}

static int arr[N];

int main(void) {
    int reps, r;
    long checksum = 0;

    for (reps = 0; reps < 30; reps++) {
        int i;
        for (i = 0; i < N; i++) arr[i] = (int)(xorshift() % 1000000);
        quicksort(arr, 0, N - 1);
        checksum += arr[0] + arr[N / 2] + arr[N - 1];
    }
    printf("quicksort checksum=%ld\n", checksum);
    return 0;
}
