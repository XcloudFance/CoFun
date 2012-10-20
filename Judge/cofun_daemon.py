import os
import sys
import time
import shutil
import MySQLdb

COMPILE_COMMAND = 'gcc __source.c -o __a.out -Wall'
COMPILE_REWRITE = ' 1> __compile_info.txt 2>&1'
EXTENSION = {
    1:  'c',
    2:  'cc',
    3:  'pas',
}
RESULT = {
    'CE'    :   1,
    'RUN'   :   2,
    'AC'    :   3,
    'WA'    :   4,
    'RE'    :   5,
    'TLE'   :   6,
    'MLE'   :   7,
}

def RemoveFiles():
    for root, dirs, files in os.walk('.', topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

def GetTasks():
    cur.execute('SELECT * FROM Submit WHERE SubmitStatus=0 ORDER BY SubmitID ASC')
    tasks = cur.fetchall()
    return tasks

def Compile():
    os.system(COMPILE_COMMAND + COMPILE_REWRITE)
    info = open('__compile_info.txt', 'r').read()
    return (os.path.exists('__a.out'), info)

def GetDiff(ansfile):
    exitcode = os.system('diff -awZB -C 5 output.txt ' + ansfile + ' > __diff.txt')
    diff = open('__diff.txt', 'r').read()
    return (exitcode, diff)

def Process(tasks):
    if not tasks:
        return
    for task in tasks:
        #print task
        os.chdir('/home/cofun/tmp')
        RemoveFiles()
        fsource = open('__source.c', 'w')
        fsource.write(task['SubmitCode'])
        fsource.close()

        (compile_success, compile_info) = Compile()
        if compile_info:
            print '%s  has compile info' % task['SubmitID']
            cur.execute('UPDATE Submit SET CompilerInfo=%s, JudgeTime=CURRENT_TIMESTAMP WHERE SubmitID=%s', (compile_info, task['SubmitID']))
        if not compile_success:
            print '%s  CE' % task['SubmitID']
            cur.execute('UPDATE Submit SET SubmitStatus=%s, JudgeTime=CURRENT_TIMESTAMP WHERE SubmitID=%s', (RESULT['CE'], task['SubmitID']))
            continue

        basedir = '/home/cofun/data/%d/' % task['ProblemID']
        final = 'AC'
        tottime = 0
        avgmem = 0
        memcnt = 0
        for line in open(basedir + 'data.config'):
            config = line.strip().split('|')
            if not config:
                continue

            # config[0]:  input file
            # config[1]:  output file
            # config[2]:  time limit
            # config[3]:  memory limit
            shutil.copyfile(basedir+config[0], '/home/cofun/tmp/input.txt')
            os.system('/home/cofun/cofun_client '+config[2]+' '+config[3])

            # RunResult   %d  (0=>NORMAL, 1=>RE, 2=>TLE, 3=>MLE)
            # TimeUsed    %d  (MicroSecond)
            # MemoryUsed  %d  (KBytes)
            # Exitcode    %d  (Exitcode or Signal code)
            result = open('/home/cofun/tmp/__result.txt', 'r').read().strip().split(' ')
            diff = result[3]
            tottime += int(result[1])
            avgmem += int(result[2])
            memcnt += 1
            if int(result[1]) > int(config[2]):
                res = 'TLE'
                final = 'TLE'
            elif int(result[2]) > int(config[3]):
                res = 'MLE'
                final = 'MLE'
            elif result[0] == '1' or result[3] != '0':
                res = 'RE'
                final = 'RE'
            else:
                (exitcode, diff) = GetDiff(basedir+config[1])
                if exitcode:
                    res = 'WA'
                    final = 'WA'
                    #print diff
                else:
                    res = 'AC'

            print '[%s]%s  on testcase [%s]  %3s  at %4dms  using %7dKBytes memory   with exitcode: %3d' % (time.strftime('%Y-%m-%d %X', time.localtime()), task['SubmitID'], config[0], res, int(result[1]), int(result[2]), int(result[3]))
            cur.execute('INSERT INTO Result (SubmitID, Result, RunTime, RunMemory, Diff) VALUES (%s, %s, %s, %s, %s)', (task['SubmitID'], RESULT[res], result[1], result[2], diff))
        cur.execute('UPDATE Submit SET SubmitStatus=%s, JudgeTime=CURRENT_TIMESTAMP, SubmitRunTime=%s, SubmitRunMemory=%s WHERE SubmitID=%s', (RESULT[final], str(tottime), str(avgmem//memcnt), task['SubmitID']))

        print '%s  -----------------------DONE------------------------' % task['SubmitID']

def main():
    global con, cur
    try:
        con = MySQLdb.connect('localhost', 'root', '123456', 'cofun')
        con.set_character_set('utf8')
        cur = con.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SET NAMES utf8;')
        cur.execute('SET CHARACTER SET utf8;')
        cur.execute('SET character_set_connection=utf8;')
    except:
        print "Connect to DB failed!"
        if con:
            con.close()
        return

    while True:
        tasks = GetTasks()
        Process(tasks)
        time.sleep(0.5)

    con.close()

if __name__ == '__main__':
    main()
