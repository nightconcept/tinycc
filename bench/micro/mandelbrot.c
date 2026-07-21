/* Mandelbrot set escape-time computation -- nested loops, floating point. */
#include <stdio.h>

int main(void) {
    int width = 1600, height = 1600;
    int max_iter = 300;
    long total = 0;
    int px, py;

    for (py = 0; py < height; py++) {
        for (px = 0; px < width; px++) {
            double x0 = (px / (double)width) * 3.5 - 2.5;
            double y0 = (py / (double)height) * 2.0 - 1.0;
            double x = 0.0, y = 0.0;
            int iter = 0;
            while (x * x + y * y <= 4.0 && iter < max_iter) {
                double xtemp = x * x - y * y + x0;
                y = 2.0 * x * y + y0;
                x = xtemp;
                iter++;
            }
            total += iter;
        }
    }
    printf("mandelbrot total=%ld\n", total);
    return 0;
}
