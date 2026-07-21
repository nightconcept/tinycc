/* Recursive Fibonacci -- exercises deep call/recursion overhead. */
#include <stdio.h>

long fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(void) {
    long r = fib(37);
    printf("fib(37)=%ld\n", r);
    return 0;
}
