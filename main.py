import psycopg2
import json
from Crypto.Cipher import AES
import argparse
import sys
import pprint


class Database:
    def __init__(self, db_init, debug_mode):
        self.__db_init = db_init
        self.__debug_mode = debug_mode

    def connect_to_database(self, database_name, user_name, password):
        self.conn = psycopg2.connect(dbname=database_name, user=user_name, password=password, host="localhost")
        self.cur = self.conn.cursor()

    def database_initialization(self, file_name):
        self.read_from_file_sql(file_name)
    
    def read_from_file_sql(self, file_name):
        f = open(file_name, 'r')
        self.cur.execute(f.read())
        self.conn.commit()
    
    def interpret_string_as_json(self, string):
        f_dict = json.loads(string)
        key = next(iter(f_dict))
        self.function_interpreter(key, f_dict[key])

    def read_from_file(self, file_name):
        f = open(file_name, 'r')
        for line in f:
            self.interpret_string_as_json(line)
        f.close()

    def user_has_privileges(self, is_leader, function_name):
        app_user_privileges = ["protest", "support", "downvote", "upvote"]
        if not is_leader and function_name not in app_user_privileges:
            return False
        return True

    def check_user_privileges(self, is_leader, function_name):
        if not self.user_has_privileges(is_leader, function_name):
            raise Exception('User has no privileges to perform action')

    def check_password(self, id, password):
        user_tuple = self.get_member_by_id(id)
        if user_tuple is not None:
            return True if self.compare_passwords(password, user_tuple[1]) else False
        return None

    def compare_passwords(self, password, db_password):
        self.cur.execute("SELECT crypt(%s, %s) = %s;", (password, db_password, db_password))
        return self.cur.fetchone()[0]

    def update_user_return_true_if_leader(self, id, password, last_activity):
        user_tuple = self.get_member_by_id(id)
        if user_tuple is not None:
            self.update_user_timestamp(id, user_tuple[1], password, user_tuple[2], last_activity, user_tuple[4])
            return user_tuple[3]
        else:
            self.insert_user(id, password, last_activity, 'false')
            return False
        

    def update_user_timestamp(self, id, user_password, password, user_timestamp, current_timestamp, is_dead):
        if self.compare_passwords(password, user_password):
            if is_dead or self.dead_user(user_timestamp, current_timestamp):
                self.cur.execute("UPDATE member SET dead='true' WHERE id=%s", (id,))
                self.conn.commit()
                raise Exception('User is dead')
            self.cur.execute("UPDATE member SET last_activity=to_timestamp(%s) WHERE id=%s;", (current_timestamp, id))
        else:
            raise Exception('Wrong password')

    def update_dead_status(self, current_timestamp):
        self.cur.execute("UPDATE member SET dead='true' WHERE last_activity + interval '1 year' <  to_timestamp(%s);", (current_timestamp, ))      

    def dead_user(self, user_timestamp, current_timestamp):
        self.cur.execute("SELECT to_timestamp(%s) >  %s + interval '1 year';", (current_timestamp, user_timestamp))
        return self.cur.fetchone()[0]

    # SELECT _START_

    def get_member_by_id(self, id):
        self.cur.execute("SELECT * FROM member WHERE id=%s;", (id,))
        return self.cur.fetchone()

    def get_project_by_id(self, id):
        self.cur.execute("SELECT * FROM project WHERE id=%s;", (id,))
        return self.cur.fetchone()
    
    # SELECT _END_

    # INSERT _START_

    def insert_user(self, id, password, last_activity, leader):
        self.cur.execute("""INSERT INTO member(id, password, last_activity, leader) 
                            VALUES(%s, crypt(%s, gen_salt('md5')), to_timestamp(%s), %s );""", (id, password, last_activity, leader));

    def insert_project(self, id, authority_id):
        self.cur.execute("SELECT * FROM authority a WHERE a.id = %s;", (authority_id,))
        if self.cur.fetchone() is None:
            self.cur.execute("INSERT INTO authority VALUES(%s);", (authority_id,))

        self.cur.execute("""INSERT INTO project(id, authority_id) 
                            VALUES(%s, %s);""", (id, authority_id));
       
    # INSERT _END_

    # Funcje API _START_

    def open_function(self, args):
        self.connect_to_database(args['database'], args['login'], args['password'])
        if self.__db_init and args['login'] == 'init':
                self.database_initialization("db_init.sql")

    def leader_function(self, args):
        self.insert_user(args['member'], str(args['password']), args['timestamp'], 'true')
    

    def check_correctness(self, name, args):
        is_leader = self.update_user_return_true_if_leader(args['member'], args['password'], args['timestamp'])
        self.check_user_privileges(is_leader, name)

    def check_project_existence(self, args):
        if self.get_project_by_id(args["project"]) is None:
            if "authority" in args:
                self.insert_project(args["project"], args["authority"])
            else:
                raise KeyError('No project with given id, please enter the authority')        
     
    def action_function(self, args):
        self.check_correctness("protest", args)
        self.check_project_existence(args)
        self.cur.execute("""INSERT INTO action(id, project_id, member_id, action_type) 
                            VALUES(%s, %s, %s %s);""", (args["action"], args["project"], args["member"]));

    def protest_function(self, args):
        self.check_correctness("protest", args)
        self.check_project_existence(args)
        self.cur.execute("""INSERT INTO action(id, project_id, member_id, action_type) 
                            VALUES(%s, %s, %s, %s);""", (args["action"], args["project"], args["member"], 'false'));

    def support_function(self, args):
        self.check_correctness("support", args)
        self.check_project_existence(args)
        self.cur.execute("""INSERT INTO action(id, project_id, member_id, action_type) 
                            VALUES(%s, %s, %s, %s );""", (args["action"], args["project"], args["member"], 'true'));
    
    #TO DO
    def user_can_vote_for_action(self, user_id, action_id):
        self.cur.execute("SELECT * FROM upvote WHERE member_id=%s AND action_id=%s;", (user_id, action_id))
        if self.cur.fetchone() is not None:
            return False
        self.cur.execute("SELECT * FROM downvote WHERE member_id=%s AND action_id=%s;", (user_id, action_id))
        if self.cur.fetchone() is not None:
            return False
        return True

    def upvote_function(self, args):
        self.check_correctness("upvote", args)
        if self.user_can_vote_for_action(args['member'], args['action']):
            self.cur.execute("""INSERT INTO upvote(member_id, action_id) 
                                VALUES(%s, %s );""", (args['member'], args['action']))
        else:
            raise Exception('User has already voted')

    def downvote_function(self, args):
        self.check_correctness("downvote", args)
        if self.user_can_vote_for_action(args['member'], args['action']):
            self.cur.execute("""INSERT INTO downvote(member_id, action_id) 
                                VALUES(%s, %s );""", (args["member"], args["action"]))
        else:
            raise Exception('User has already voted')

    def actions_function(self, args):
        self.check_correctness("actions", args)
        if 'type' in args and 'project' not in args and 'authority' not in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s", (args["type"], ))
        elif 'type' in args and 'project' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s AND project_id=%s ", (args["type"], args['project'] ))
        elif 'type' in args and 'authority' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s AND authority_id=%s", (args["type"], args['authority'] ))
        elif 'project' in args :
            self.cur.execute("SELECT * FROM action_and_votes_view where project_id=%s", (args["project"], ))
        elif 'authority' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where authority_id=%s", (args['authority'], ))
        else:
            self.cur.execute("SELECT * FROM action_and_votes_view")

        self.data = self.cur.fetchall()

    def projects_function(self, args):
        self.check_correctness("actions", args)
        if 'authority' in args:
            self.cur.execute("SELECT * FROM project WHERE authority_id = %s ORDER BY id", (args['authority'], ))
        else:
            self.cur.execute("SELECT * FROM project ORDER BY id")
        self.data = self.cur.fetchall()


    
    def votes_function(self, args):
        self.check_correctness("votes", args)
        if 'action' in args:
            self.cur.execute("""
            WITH UP AS
                (SELECT member_id, COUNT(*) AS upvote_number
                FROM upvote
                WHERE action_id = 500
                GROUP BY member_id),
            DOWN AS
                (SELECT member_id, COUNT(*) AS downvote_number
                FROM downvote
                WHERE action_id = 500
                GROUP BY member_id)
            (SELECT m.id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
            (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END )
            FROM member m
                LEFT JOIN UP ON(UP.member_id = m.id)
                LEFT JOIN DOWN ON (DOWN.member_id = m.id)
            )
            ORDER BY m.id;""", (args["action"], args["action"]))
        elif 'project' in args:
            self.cur.execute("""
            WITH UP AS
                (SELECT u.member_id, COUNT(*) AS upvote_number
                FROM upvote u
                    JOIN action a ON (a.id = u.action_id)
                WHERE project_id = %s
                GROUP BY u.member_id),
            DOWN AS
                (SELECT d.member_id, COUNT(*) AS downvote_number
                FROM downvote d
                    JOIN action a ON (a.id = d.action_id)
                WHERE project_id = %s
                GROUP BY d.member_id)
            (SELECT m.id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
            (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END )
            FROM member m
                LEFT JOIN UP ON(UP.member_id = m.id)
                LEFT JOIN DOWN ON (DOWN.member_id = m.id)
            )
            ORDER BY m.id""", (args['project'], args['project']))
        else:
            self.cur.execute("SELECT * FROM member_and_votes_view")
        self.data = self.cur.fetchall()

    def trolls_function(self, args):
        self.update_dead_status(args['timestamp'])
        self.cur.execute("""SELECT id, upvotes, downvotes, dead
                            FROM member
                            WHERE downvotes-upvotes > 0
                            ORDER BY downvotes-upvotes;""")
        self.data = self.cur.fetchall()
        

        

    # funkcje API _END_

    def function_interpreter(self, name, args):
        self.data = None
        error_occured = False
        try:
            (lambda function_name : {
                "open" : lambda args : self.open_function(args),
                "leader" : lambda args : self.leader_function(args),
                "protest" : lambda args : self.protest_function(args),
                "support" : lambda args : self.support_function(args),
                "upvote" : lambda args : self.upvote_function(args),
                "downvote" : lambda args : self.downvote_function(args),
                "actions" : lambda args : self.actions_function(args),
                "projects" : lambda args : self.projects_function(args),
                "votes" : lambda args : self.votes_function(args),
                "trolls" : lambda args : self.trolls_function(args)}[function_name]
            )(name)(args)
        except Exception as e:
            if self.__debug_mode:
                if hasattr(e, 'message'):
                    print(e.message)
                else:
                    print(e)
            self.conn.rollback()
            error_occured = True
        print(self.status(error_occured, self.data))

    
    def start_stream(self):
        while 1:
            try: 
                line = sys.stdin.readline()
                if not line:
                    break
                self.interpret_string_as_json(line)
            except KeyboardInterrupt:
                break


    def status(self, error_occured, data):
        if not error_occured:
            try:
                self.conn.commit()
            except Exception as e:
                error_occured = True

        if error_occured:
            return json.dumps({'status': 'ERROR'})
        else:
            if data is None:
                return json.dumps({'status': 'OK'})
            else:
                data2 = []
                for i in data:
                    data2.append(str(i))
                return json.dumps({'status': 'OK', 'data' :data2 }, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Projekt: System Zarządzania Partią Polityczną')
    parser.add_argument("-i","--init", help="initialization of database", action="store_true")
    parser.add_argument("-g","--debug", help="show information about errors", action="store_true")
    parser.add_argument("-f", "--filename", nargs=1, help="name of the file with JSON objects", type=str)
    args = parser.parse_args()
    db = Database(args.init, args.debug)
    if (args.filename is not None):
        db.read_from_file(args.filename[0])
    else:
        db.start_stream()

    db.cur.close()
    db.conn.close()

    print("END")


if __name__ == "__main__":
    main()


