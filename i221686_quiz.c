#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
 
#define N 1000
 
int main() {
 
    int A[N], B[N];
    int SUM = 0;
    int MAX = 0;
    int total_threads = 0;
    int workload[100];
 
    // Initialize workload array to zero
    int i;
    for (i = 0; i < 100; i++)
        workload[i] = 0;
 
    // Initialize array A with random values (1-100)
    srand(15);
    for (i = 0; i < N; i++)
        A[i] = rand() % 100 + 1;
 
    // ── Parallel Region ──────────────────────────────────────────
    #pragma omp parallel default(none) \
        shared(A, B, workload, total_threads) \
        private(i) \
        reduction(+:SUM) reduction(max:MAX)
    {
        int tid = omp_get_thread_num();
 
        // Capture total number of threads (runs once)
        #pragma omp single
        total_threads = omp_get_num_threads();
 
        // Compute B[i] = A[i]*A[i] + 5 using dynamic scheduling
        #pragma omp for schedule(dynamic, 10)
        for (i = 0; i < N; i++) {
 
            B[i] = A[i] * A[i] + 5;
 
            // Count work done by each thread
            workload[tid]++;
 
            // Reduction for SUM and MAX
            SUM += B[i];
            if (B[i] > MAX) MAX = B[i];
 
            // Critical section: log first 20 elements only
            #pragma omp critical
            {
                if (i < 20)
                    printf("Thread %d processed index %d\n", tid, i);
            }
        }
 
        // Barrier: all threads must finish before printing
        #pragma omp barrier
 
        // Master thread prints all final results
        #pragma omp master
        {
            // Print first 20 elements of A and B
            printf("\n--- First 20 Elements of A and B ---\n");
            printf("%-8s %-8s %-8s\n", "Index", "A[i]", "B[i]");
            for (int j = 0; j < 20; j++)
                printf("%-8d %-8d %-8d\n", j, A[j], B[j]);
 
            // Print total threads
            printf("\nTotal Threads Used: %d\n", total_threads);
 
            // Print work distribution per thread
            printf("\n--- Work Distribution per Thread ---\n");
            for (int j = 0; j < total_threads; j++)
                printf("Thread %d handled %d elements\n", j, workload[j]);
 
            // Print final SUM and MAX
            printf("\nFinal SUM = %d\n", SUM);
            printf("Final MAX = %d\n", MAX);
        }
 
    } // end parallel region
 
    return 0;
}
