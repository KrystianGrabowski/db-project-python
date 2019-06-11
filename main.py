import psycopg2
import json
import argparse
import sys

class Database:
    """
    Baza do zarzadzania baza danych partii politycznej
    """
    def __init__(self, db_init, debug_mode):
        """ Ustawia trybu debugowania oraz inicjalizacji  

        Parameters:
            db_init (bool): inicjalizacja bazy danych
            debug_mode (bool): tryb debugowania
        """
        self.__db_init = db_init
        self.__debug_mode = debug_mode

    def connect_to_database(self, database_name, user_name, password):
        """ Ustanawia polaczenie z baza danych

        Parameters:
            database_name (str): nazwa bazy danych
            user_name (str): nazwa uzytkownika
            password (str): haslo uzytkownika
        """
        self.conn = psycopg2.connect(dbname=database_name, user=user_name, password=password, host="localhost")
        self.cur = self.conn.cursor()

    def database_initialization(self, file_name):
        """ Ustanawia polaczenie z baza danych

        Parameters:
            file_name (str): nazwa pliku z polecami tworzacymi elementy bazy
        """
        self.read_from_file_sql(file_name)
    
    def read_from_file_sql(self, file_name):
        """Czyta z pliku polecenia sql oraz je wykonuje

        Parameters:
            file_name (str): nazwa pliku z polecami sql
        """
        f = open(file_name, 'r')
        self.cur.execute(f.read())
        self.conn.commit()
    
    def interpret_string_as_json(self, string):
        """Przeksztalca napis na slownik oraz przekazuje go do funkcji,
        ktora wykona polecenia w nim zawarte

        Parameters:
            string (str): napis bedacy obiektem JSON
        """
        f_dict = json.loads(string)
        key = next(iter(f_dict))
        self.function_interpreter(key, f_dict[key])

    def read_from_file(self, file_name):
        """Wczytuje z pliku obiekty JSON

        Parameters:
            file_name (str): nazwa pliku
        """
        f = open(file_name, 'r')
        for line in f:
            self.interpret_string_as_json(line)
        f.close()

    def user_has_privileges(self, is_leader, function_name):
        """Sprawdza czy uzytkownik ma uprawnienia aby wywolac
        funkcje

        Parameters:
            is_leader (bool): informuje czy uzytkownik jest leaderem
            function_name (str): nazwa funkcji
        
        Return:
            (bool) True jesli uzytkownik moze wykonac akcje False wpp
        """
        if self.__init_user:
            return True
        app_user_privileges = ["protest", "support", "downvote", "upvote"]
        if not is_leader and function_name not in app_user_privileges:
            return False
        return True

    def check_user_privileges(self, is_leader, function_name):
        """Sprawdza czy uzytkownik ma uprawnienia aby wywolac
        funkcje. Jesli nie ma uprawnien zglasza wyjatek

        Parameters:
            is_leader (bool): informuje czy uzytkownik jest leaderem
            function_name (str): nazwa funkcji
        """
        if not self.user_has_privileges(is_leader, function_name):
            raise Exception('User has no privileges to perform action')

    def check_password(self, id, password):
        """Sprawdza czy haslem uzytkownika o identyfikatorze id
        jest password

        Parameters:
            id (int): identyfikator uzytkownika
            password (str): haslo podane przez uzytkownika
        
        Return:
            (bool): True jesli hasla sie zgadzaja False wpp
            None: jesli uzytkownik nie istnieje
        """
        
        user_tuple = self.get_member_by_id(id)
        if user_tuple is not None:
            return True if self.compare_passwords(password, user_tuple[1]) else False
        return None

    def compare_passwords(self, password, db_password):
        """Sprawdza za pomoca modulu pgcrypto czy haslo password
        odpowiada zaszyfrowanemu haslu db_password 

        Parameters:
            password (str): haslo podane przez uzytkownika
            db_password (str): zaszyfrowane haslo z bazy danych
        
        Return:
            (bool): True jesli hasla sie zgadzaja False wpp
        """
        self.cur.execute("SELECT crypt(%s, %s) = %s;", (password, db_password, db_password))
        return self.cur.fetchone()[0]

    def update_user_return_true_if_leader(self, id, password, last_activity):
        """Sprawdza czy uzytkownik istnieje w bazie. Jesli istnieje to aktualizuje jego
        czas ostatniej aktywnosci. Jesli nie istnieje to go tworzy.

        Parameters:
            id (int): identyfikator uzytkownika
            password (str): haslo podane przez uzytkownika
            last_activity (int): UNIX timestamp
        
        Return:
            (bool): True jesli user jest liderem False wpp
        """
        user_tuple = self.get_member_by_id(id)
        if user_tuple is not None:
            self.update_user_timestamp(id, user_tuple[1], password, user_tuple[2], last_activity, user_tuple[4])
            return user_tuple[3]
        else:
            self.insert_user(id, password, last_activity, 'false')
            return False
        

    def update_user_timestamp(self, id, user_password, password, user_timestamp, current_timestamp, is_dead):
        """Aktualizuje czas ostatniej aktywnosci uzytkownika. W przypadku zlego hasla
        lub zamrozenia zglasza wyjatek

        Parameters:
            id (int): identyfikator uzytkownika
            user_password (str): zaszyfrowane haslo z bazy danych 
            password (str): haslo podane przez uzytkownika
            user_timestamp (int): czas ostatniej aktywnosci usera, UNIX timestamp
            current_timestamp (int): UNIX timestamp
            is_dead (bool): status zamrozenia uzytkownika
        """
        if self.compare_passwords(password, user_password):
            if is_dead or self.dead_user(user_timestamp, current_timestamp):
                self.cur.execute("UPDATE member SET dead='true' WHERE id=%s", (id,))
                self.conn.commit()
                raise Exception('User is dead')
            self.cur.execute("UPDATE member SET last_activity=to_timestamp(%s) WHERE id=%s;", (current_timestamp, id))
        else:
            raise Exception('Wrong password')

    def update_dead_status(self, current_timestamp):
        """Aktualizuje status zamrozenia wszystkich uzytkownikow

        Parameters:
            current_timestamp (int): UNIX timestamp
        """
        self.cur.execute("UPDATE member SET dead='true' WHERE last_activity + interval '1 year' <  to_timestamp(%s);", (current_timestamp, ))      

    def dead_user(self, user_timestamp, current_timestamp):
        """Sprawdza czy uzytkownik byl nieaktywny dluzej niz rok

        Parameters:
            user_timestamp (int): czas ostatniej aktywnosci usera, UNIX timestamp
            current_timestamp (int): UNIX timestamp
        
        Return:
            True jesli uzytkownik jest zamrozony False wpp
        """
        self.cur.execute("SELECT to_timestamp(%s) >  %s + interval '1 year';", (current_timestamp, user_timestamp))
        return self.cur.fetchone()[0]

    # SELECT _START_

    def get_member_by_id(self, id):
        """Zwraca krotke uzytkownika o podanym id

        Parameters:
            id (int): identyfikator uzytkownika

        Return:
            Krotka z danymi uzytkownika
        """
        self.cur.execute("SELECT * FROM member WHERE id=%s;", (id,))
        return self.cur.fetchone()

    def get_project_by_id(self, id):
        """Zwraca krotke projektu o podanym id

        Parameters:
            id (int): identyfikator projektu

        Return:
            Krotka z danymi projektu
        """
        self.cur.execute("SELECT * FROM project WHERE id=%s;", (id,))
        return self.cur.fetchone()
    
    # SELECT _END_

    # INSERT _START_

    def id_exists(self, id):
        """Sprawdza czy identyfikator istnieje w bazie.
        Jesli tak zglasza wyjatek

        Parameters:
            id (int): identyfikator

        """
        self.cur.execute("SELECT index_exists(%s);", (id, ))
        if self.cur.fetchone()[0]:
            raise Exception("ID already exists")

    def id_exists_in_column(self, id_dict):
        """Sprawdza czy identyfikatory istnieje w odpowiednich tabelach.
        Jesli ktorys identyfikator nie istnieje zglasza wyjatek

        Parameters:
            id_dict (int): slownik zawierajacy nazwy tabel oraz identyfikatory
        """
        if 'authority' in id_dict:
            self.cur.execute("SELECT authority_exists(%s);", (id_dict['authority'], ))
            if not self.cur.fetchone()[0]:
                raise Exception("ID(authority) does not exist")

        if 'member' in id_dict:
            self.cur.execute("SELECT member_exists(%s);", (id_dict['member'], ))
            if not self.cur.fetchone()[0]:
                raise Exception("ID(member) does not exist")

        if 'project' in id_dict:
            self.cur.execute("SELECT project_exists(%s);", (id_dict['project'], ))
            if not self.cur.fetchone()[0]:
                raise Exception("ID(project) does not exist")

        if 'action' in id_dict:
            self.cur.execute("SELECT action_exists(%s);", (id_dict['action'], ))
            if not self.cur.fetchone()[0]:
                raise Exception("ID(action) does not exist")

    def fields_have_different_id(self, name, args):
        """Sprawdza czy odpowiednie pola w pojedynczym wywolaniu funkcji maja
        rozne identyfikatory. Jesli odpowiednie pola maja te same identyfikatory
        zglaszany jest wyjatek

        Parameters:
            name (str): nazwa funkcji
            args (int): slownik zawierajacy dane przekazane do funkcji
        """
        if name == "protest" or name == "support":
            id_arr = [args["member"], args["action"], args["project"]]
            if 'authority' in args:
                id_arr.append(args['authority'])

        elif name == "upvote" or name == "downvote":
            id_arr = [args["member"], args["action"]]

        elif name == "actions":
            id_arr = [args["member"]]
            if 'project' in args:
                id_arr.append(args["project"])
            if 'authority' in args:
                id_arr.append(args["authority"])
        
        elif name == "projects":
            id_arr = [args["member"]]
            if 'authority' in args:
                id_arr.append(args["authority"])

        elif name == "votes":
            id_arr = [args["member"]]
            if 'project' in args:
                id_arr.append(args["project"])
            if 'action' in args:
                id_arr.append(args["action"])

        if len(id_arr) != len(set(id_arr)):
            raise Exception("Two or more fields have the same value")

    def insert_user(self, id, password, last_activity, leader):
        """Dodaje uzytkownika do tabeli member nadajac mu podane parametry

        Parameters:
            id (int): identyfikator uzytkownika
            password (str): haslo uzytkownika
            last_activity (int): UNIX timestamp
            leader (bool): informuje czy uzytkownik jest leaderem
        """
        self.id_exists(id)
        self.cur.execute("""INSERT INTO member(id, password, last_activity, leader) 
                            VALUES(%s, crypt(%s, gen_salt('md5')), to_timestamp(%s), %s );""", (id, password, last_activity, leader));

    def insert_project(self, id, authority_id):
        """Dodaje uzytkownika do tabeli member nadajac mu podane parametry

        Parameters:
            id (int): identyfikator uzytkownika
            password (str): haslo uzytkownika
            last_activity (int): UNIX timestamp
            leader (bool): informuje czy uzytkownik jest leaderem
        """
        self.id_exists(id)
        self.cur.execute("SELECT * FROM authority a WHERE a.id = %s;", (authority_id,))
        if self.cur.fetchone() is None:
            self.id_exists(authority_id)
            self.cur.execute("INSERT INTO authority VALUES(%s);", (authority_id,))

        self.cur.execute("""INSERT INTO project(id, authority_id) 
                            VALUES(%s, %s);""", (id, authority_id));
       
    # INSERT _END_

    # Funcje API _START_

    def open_function(self, args):
        """Otwiera polaczenie z baza danych za pomoca podanych danych logowania

        Format: 
            open <database> <login> <password> 

        Parameters:
            args (dict): dane logowania do bazy
        """
        if args['login'] == 'init':
            self.__init_user = True
        else:
            self.__init_user= False
        self.connect_to_database(args['database'], args['login'], args['password'])
        
        if self.__db_init and args['login'] == 'init':
            self.database_initialization("db_init.sql")
            

    def leader_function(self, args):
        """Dodaje nowego uzytkownika ktory zostaje leaderem

        Format: 
            leader <timestamp> <password> <member>

        Parameters:
            args (dict): dane nowego uzytkownika
        """
        self.insert_user(args['member'], str(args['password']), args['timestamp'], 'true')
    

    def check_correctness(self, name, args):
        """Aktualizuje czas aktywnosci uzytkownika oraz zapewnia ze wszystkie warunki
        zostaly spelnione aby poprawnie przeprowadzic operacje

        Parameters:
            name (str) : nazwa funkcji
            args (dict): dane nowego uzytkownika
        """
        is_leader = self.update_user_return_true_if_leader(args['member'], args['password'], args['timestamp'])
        self.check_user_privileges(is_leader, name)

    def check_project_existence(self, args):
        """Sprawdza czy projekt istnieje w bazie danych. W przypadku braku
        projektu w bazie oraz braku organu wladzy w args zglasza wyjatek

        Parameters:
            args (dict): slownik zawierajacy dane projektu
        """
        if self.get_project_by_id(args["project"]) is None:
            if "authority" in args:
                self.insert_project(args["project"], args["authority"])
            else:
                raise KeyError('No project with given id, please enter the authority')        

    def protest_function(self, args):
        """Dodaje protest do bazy danych

        Format: 
            protest <timestamp> <member> <password> <action> <project> [ <authority> ]

        Parameters:
            args (dict): slownik zawierajacy dane akcji
        """
        self.fields_have_different_id("protest", args)
        self.id_exists(args["action"])
        self.check_correctness("protest", args)
        self.check_project_existence(args)
        self.cur.execute("""INSERT INTO action(id, project_id, member_id, action_type) 
                            VALUES(%s, %s, %s, %s);""", (args["action"], args["project"], args["member"], 'false'));

    def support_function(self, args):
        """Dodaje wsparcie do bazy danych

        Format: 
            support <timestamp> <member> <password> <action> <project> [ <authority> ]

        Parameters:
            args (dict): slownik zawierajacy dane akcji
        """
        self.fields_have_different_id("support", args)
        self.id_exists(args["action"])
        self.check_correctness("support", args)
        self.check_project_existence(args)
        self.cur.execute("""INSERT INTO action(id, project_id, member_id, action_type) 
                            VALUES(%s, %s, %s, %s );""", (args["action"], args["project"], args["member"], 'true'));
    

    def user_can_vote_for_action(self, user_id, action_id):
        """Sprawdza czy uzytkownik ma prawo glosowac w akcji

        Parameters:
            user_id (int): identyfikator uzytkownika
            action_id (int): identyfikator akcji

        Return:
            (bool) True jesli uzytkownk moze glosowac w akcji False wpp
        """
        self.cur.execute("SELECT * FROM upvote WHERE member_id=%s AND action_id=%s;", (user_id, action_id))
        if self.cur.fetchone() is not None:
            return False
        self.cur.execute("SELECT * FROM downvote WHERE member_id=%s AND action_id=%s;", (user_id, action_id))
        if self.cur.fetchone() is not None:
            return False
        return True

    def upvote_function(self, args):
        """Dodaje glos na akcje do bazy danych

        Format: 
            upvote <timestamp> <member> <password> <action> 

        Parameters:
            args (dict): slownik zawierajacy dane glosu
        """
        self.fields_have_different_id("upvote", args)
        self.id_exists_in_column({'action': args['action']})
        self.check_correctness("upvote", args)
        if self.user_can_vote_for_action(args['member'], args['action']):
            self.cur.execute("""INSERT INTO upvote(member_id, action_id) 
                                VALUES(%s, %s );""", (args['member'], args['action']))
        else:
            raise Exception('User has already voted')

    def downvote_function(self, args):
        """Dodaje glos na akcje do bazy danych

        Format: 
            downvote <timestamp> <member> <password> <action>

        Parameters:
            args (dict): slownik zawierajacy dane glosu
        """
        self.fields_have_different_id("downvote", args)
        self.id_exists_in_column({'action': args['action']})
        self.check_correctness("downvote", args)
        if self.user_can_vote_for_action(args['member'], args['action']):
            self.cur.execute("""INSERT INTO downvote(member_id, action_id) 
                                VALUES(%s, %s );""", (args["member"], args["action"]))
        else:
            raise Exception('User has already voted')

    def actions_function(self, args):
        """Zwraca liste wszystkich akcji. Jesli podano typ, projekt/organ wladzy
        to ogranicza sie tylko do akcji o wspomnianym typie

        Format: 
            actions <timestamp> <member> <password> [ <type> ] [ <project> | <authority> ] 

        Parameters:
            args (dict): slownik zawierajacy dane glosu

        SQL:
            <action> <type> <project> <authority> <upvotes> <downvotes>
        """
        self.fields_have_different_id("actions", args)
        self.check_correctness("actions", args)
        if 'type' in args:
            if args['type'] != 'support' and args['type'] != 'protest':
                raise Exception("Unknown action type")

        if 'project' in args:
            self.id_exists_in_column({'project': args['project']})
        
        if 'authority' in args:
            self.id_exists_in_column({'authority': args['authority']})

        if 'type' in args and 'project' not in args and 'authority' not in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s ORDER BY id;", (args["type"], ))
        elif 'type' in args and 'project' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s AND project_id=%s ORDER BY id;", (args["type"], args['project'] ))
        elif 'type' in args and 'authority' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where action_type=%s AND authority_id=%s ORDER BY id;", (args["type"], args['authority'] ))
        elif 'project' in args :
            self.cur.execute("SELECT * FROM action_and_votes_view where project_id=%s ORDER BY id;", (args["project"], ))
        elif 'authority' in args:
            self.cur.execute("SELECT * FROM action_and_votes_view where authority_id=%s ORDER BY id;", (args['authority'], ))
        else:
            self.cur.execute("SELECT * FROM action_and_votes_view ORDER BY id;")

        self.data = self.cur.fetchall()

    def projects_function(self, args):
        """Zwraca liste wszystkich dzialan wraz z id organu wladzy. Jesli podano
        organ wladzy ogranicza sie tylko do projektow pod jego zarzadem

        Format: 
            projects <timestamp> <member> <password> [ authority ]

        Parameters:
            args (dict): slownik zawierajacy dane

        SQL:
            <project> <authority>
        """
        self.fields_have_different_id("projects", args)
        if 'authority' in args:
            self.id_exists_in_column({'authority': args['authority']})
        self.check_correctness("actions", args)
        if 'authority' in args:
            self.cur.execute("SELECT * FROM project WHERE authority_id = %s ORDER BY id", (args['authority'], ))
        else:
            self.cur.execute("SELECT * FROM project ORDER BY id")
        self.data = self.cur.fetchall()


    
    def votes_function(self, args):
        """Zwraca liste wszystkich czlonkow wraz 
        liczbami oddanych przez nich glosow za i przeciw. Jesli podano akcje/projekt 
        to ogranicza sie tylko glosow z nimi zwiazanymi.

        Format: 
            votes <timestamp> <member> <password> [ <action> | <project> ]

        Parameters:       
            args (dict): slownik zawierajacy dane

        SQL:
            <member> <upvotes> <downvotes>
        """
        self.fields_have_different_id("votes", args)
        if 'action' in args:
            self.id_exists_in_column({'action': args['action']})
        if 'project' in args:
            self.id_exists_in_column({'project': args['project']})

        self.check_correctness("votes", args)
        if 'action' in args:
            self.cur.execute("SELECT * FROM member_and_votes_action(%s)", (args["action"], ))
        elif 'project' in args:
            self.cur.execute("SELECT * FROM member_and_votes_project(%s)", (args['project'], ))
        else:
            self.cur.execute("SELECT * FROM member_and_votes_view")
        self.data = self.cur.fetchall()

    def trolls_function(self, args):
        """Zwraca liste wszystkich uzytkownikow, ktorzy zaproponowali akcje 
        majace sumarycznie wiecej downvotes niz upvotes na chwile podana w args

        Format: 
            trolls <timestamp>

        Parameters:      
            args (dict): slownik zawierajacy dane
             
        SQL:
            <member> <upvotes> <downvotes> <active>
        """
        self.update_dead_status(args['timestamp'])
        self.cur.execute("""SELECT id, upvotes, downvotes, 
                                (CASE WHEN dead = FALSE THEN 'true' ELSE 'false' END)
                            FROM member
                            WHERE downvotes-upvotes > 0
                            ORDER BY downvotes-upvotes, id;""")
        self.data = self.cur.fetchall()
        

        

    # funkcje API _END_

    def function_interpreter(self, name, args):
        """Interpretuje funkcje za pomoca lambda wyrazenia przekazujac sterowanie 
        do odpowiedniej funkcji. Wywoluje funkcje zwracajaca status

        Parameters:       
            name (str): nazwa funkcji
            args (dict): slownik zawierajacy dane
        """
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
            error_occured = True
        print(self.status(error_occured, self.data))

    
    def start_stream(self):
        """Otwiera strumien wejscia
        """
        while 1:
            try: 
                line = sys.stdin.readline()
                if not line:
                    break
                self.interpret_string_as_json(line)
            except KeyboardInterrupt:
                break


    def status(self, error_occured, data):
        """Zwraca status operacji. Jesli nie wystapil zaden blad 
        zatwierdza zmiany wprowadzone w bazie oraz zwraca status OK z danymi.
        Jesli wystapil blad zwraca status error

        Parameters:   
            error_occured (bool): status wystapienia bledu
            data (arr): tablica zawierajaca dane zwrocone przez zapytanie sql

        Return:
            Obiekt JSON
        """
        try:
            if not error_occured:
                self.conn.commit()
            else:
                self.conn.rollback()
        except Exception as e:
            error_occured = True

        if error_occured:
            return json.dumps({'status': 'ERROR'})
        else:
            if data is None:
                return json.dumps({'status': 'OK'})
            else:
                return json.dumps({'status': 'OK', 'data' :data })

def main():
    parser = argparse.ArgumentParser(description='Projekt: System Zarzadzania Partia Polityczna')
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


if __name__ == "__main__":
    main()


