import re
import subprocess
import json

def call_and_compare(filename):
    if "init" in filename:
        stdoutdata = subprocess.getoutput("python3 main.py --init -f 'testy/{}.in.json'".format(filename))
    else:
        stdoutdata = subprocess.getoutput("python3 main.py -f 'testy/{}.in.json'".format(filename))
    result = compare("testy/{}.out.json".format(filename), stdoutdata)
    to_prt = "OK" if result else "FAIL"
    print("{} {}".format(filename, to_prt))

def compare(outputfile, stdoutdata):
    stdoutdata = stdoutdata.split("\n")
    f = open(outputfile, 'r')
    it = 0
    for line in f:
        a = json.loads(line)
        b = json.loads(stdoutdata[it])
        it += 1
        if 'data' in a and 'data' in b:
            if a["status"] != b["status"]:
                return False
            if a["data"] != b["data"]:
                    return False

        if 'data' not in a and 'data' not in b:
            if a["status"] != b["status"]:
                return False
    return True
                



def main():
    f = open('names.txt', 'r')
    it = 1
    for line in f:
        if "init" in line:
            subprocess.run(["psql", "postgres", "-f", "resetdb.sql"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        line = line.strip('\n')
        call_and_compare(line)

if __name__ == "__main__":
    main()
