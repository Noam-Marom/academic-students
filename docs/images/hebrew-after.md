## ההבדל בין fork ל-exec

הקריאה `fork` יוצרת תהליך חדש (child) שהוא עותק של תהליך האב (parent), והקריאה `exec` מחליפה את התוכנית שרצה בתהליך הנוכחי בתוכנית אחרת. בדרך כלל משלבים את השתיים: קודם מבצעים `fork`, ואז ה-child מריץ את הקריאה `exec` בקוד שלו.

| נושא | הקריאה fork | הקריאה exec |
|---|---|---|
| מה היא עושה | יוצרת תהליך חדש | מחליפה את הקוד של התהליך הקיים |
| מספר תהליכים | גדל באחד | נשאר זהה |
| ה-PID | לילד יש PID חדש | ה-PID לא משתנה |
| ערך החזרה | אפס בילד, וה-PID של הילד באב | לא חוזרת בהצלחה |
| זיכרון | עותק (copy-on-write) | נטען מחדש מהתוכנית החדשה |

להלן דוגמת קוד:

```c
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

int main(void) {
    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }
    if (pid == 0) {
        /* child: replace this program with ls */
        execlp("ls", "ls", "-l", (char *)NULL);
        perror("execlp");   /* reached only if exec failed */
        _exit(1);
    }
    /* parent: wait for the child to finish */
    waitpid(pid, NULL, 0);
    printf("child finished\n");
    return 0;
}
```

בקוד הזה האב ממתין עם `waitpid` עד שהילד מסיים, והילד מריץ את הפקודה `ls` במקום התוכנית המקורית. השורה שאחרי `execlp` תתבצע רק אם ה-exec נכשל.
