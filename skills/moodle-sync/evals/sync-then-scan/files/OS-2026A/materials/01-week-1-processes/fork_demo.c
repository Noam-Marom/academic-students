#include <stdio.h>
#include <unistd.h>

int main(void) {
    pid_t pid = fork();
    if (pid == 0) {
        printf("child\n");
    } else {
        printf("parent of %d\n", pid);
    }
    return 0;
}
