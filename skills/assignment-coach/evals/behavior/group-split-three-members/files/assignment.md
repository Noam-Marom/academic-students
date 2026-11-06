# Operating Systems — HW4 (group of 3)

Submit one PDF and one code archive per group. All members are examined on the whole submission.

1. (15 pts) Explain the difference between a process and a thread; give one case where each is preferable.
2. (30 pts) Implement a bounded producer–consumer queue in C with pthread mutexes and condition variables.
3. (20 pts) Write a test harness for the queue from Q2 (4 producers, 4 consumers, 10^6 items).
4. (20 pts) Measure throughput of your queue from Q2 with 1, 2, 4 and 8 threads using the harness from Q3; plot the results.
5. (15 pts) Explain the deadlock that occurs if the condition-variable wait in Q2 is not inside a while loop.
