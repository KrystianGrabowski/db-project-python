import psycopg2
import json
from Crypto.Cipher import AES
import sys
import getopt
import argparse


print("Hello")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "init"])
    except getopt.GetoptError:
        usage()                         
        sys.exit(2)
    for o, a in opts:
        if opt in ("-h", "--help"):
            #usage()                   
            sys.exit(0)                               
        elif opt in ("--init"):
            grammar = arg

def usage():
    parser = argparse.ArgumentParser(description='')


if __name__ == "__main__":
    main()


