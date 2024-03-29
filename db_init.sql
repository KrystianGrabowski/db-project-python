CREATE TABLE authority (
    id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE member (
    id int4 NOT NULL, 
    password varchar(128) NOT NULL, 
    last_activity timestamp NOT NULL, 
    leader bool DEFAULT 'false' NOT NULL, 
    dead bool DEFAULT 'false' NOT NULL, 
    upvotes int4 DEFAULT 0 NOT NULL, 
    downvotes int4 DEFAULT 0 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE project (
    id int4 NOT NULL, 
    authority_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE action (
    id int4 NOT NULL, 
    project_id int4 NOT NULL, 
    member_id int4 NOT NULL,
    action_type bool NOT NULL,
    PRIMARY KEY (id)
);
CREATE TABLE upvote (
    member_id int4 NOT NULL, 
    action_id int4 NOT NULL,
    PRIMARY KEY (member_id, action_id)
);
CREATE TABLE downvote (
    member_id int4 NOT NULL, 
    action_id int4 NOT NULL, 
    PRIMARY KEY (member_id, action_id)
);

ALTER TABLE project ADD CONSTRAINT authority_owns_project FOREIGN KEY (authority_id) REFERENCES authority (id);
ALTER TABLE downvote ADD CONSTRAINT member_can_downvote FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE upvote ADD CONSTRAINT member_can_upvote FOREIGN KEY (member_id) REFERENCES member (id);

ALTER TABLE action ADD CONSTRAINT member_creates_action FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE action ADD CONSTRAINT action_has_project FOREIGN KEY (project_id) REFERENCES project (id);

ALTER TABLE downvote ADD CONSTRAINT action_has_downvote FOREIGN KEY (action_id) REFERENCES action(id);
ALTER TABLE upvote ADD CONSTRAINT action_has_upvote FOREIGN KEY (action_id) REFERENCES action(id);

CREATE OR REPLACE FUNCTION update_member_upvotes() RETURNS TRIGGER AS $X$
    BEGIN
        WITH action_creator AS
        (SELECT a.member_id
            FROM action a
            WHERE a.id = NEW.action_id
            LIMIT 1)
        UPDATE member m SET upvotes = upvotes + 1 FROM action_creator
        WHERE m.id = action_creator.member_id;
    RETURN NULL;
    END
$X$ LANGUAGE plpgsql;

CREATE TRIGGER on_insert_to_upvotes AFTER INSERT ON upvote
FOR EACH ROW EXECUTE PROCEDURE update_member_upvotes();

CREATE OR REPLACE FUNCTION update_member_downvotes() RETURNS TRIGGER AS $X$
    BEGIN
        WITH action_creator AS
        (SELECT a.member_id
            FROM action a
            WHERE a.id = NEW.action_id
            LIMIT 1)
        UPDATE member m SET downvotes = downvotes + 1 FROM action_creator
        WHERE m.id = action_creator.member_id;
    RETURN NULL;
    END
$X$ LANGUAGE plpgsql;

CREATE TRIGGER on_insert_to_downvotes AFTER INSERT ON downvote
FOR EACH ROW EXECUTE PROCEDURE update_member_downvotes();

CREATE VIEW action_and_votes_view
  (id, action_type, project_id, authority_id, upvotes, downvotes)
AS
WITH UP AS
    (SELECT action_id, COUNT(*) AS upvote_number
    FROM upvote
    GROUP BY action_id),
DOWN AS
    (SELECT action_id, COUNT(*) AS downvote_number
    FROM downvote
    GROUP BY action_id)
(SELECT a.id, (CASE WHEN action_type = TRUE THEN 'support' ELSE 'protest' END),
    a.project_id, p.authority_id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
    (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END)
FROM action a
    JOIN project p ON(a.project_id = p.id)
    LEFT JOIN UP ON(UP.action_id = a.id)
    LEFT JOIN DOWN ON (DOWN.action_id = a.id)
);

CREATE VIEW member_and_votes_view
  (id, upvotes, downvotes)
AS
WITH UP AS
    (SELECT member_id, COUNT(*) AS upvote_number
    FROM upvote
    GROUP BY member_id),
DOWN AS
    (SELECT member_id, COUNT(*) AS downvote_number
    FROM downvote
    GROUP BY member_id)
(SELECT m.id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
   (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END )
FROM member m
    LEFT JOIN UP ON(UP.member_id = m.id)
    LEFT JOIN DOWN ON (DOWN.member_id = m.id)
ORDER BY m.id
);


CREATE OR REPLACE FUNCTION member_and_votes_action (INT) 
   RETURNS TABLE (
    id int4, 
    upvotes bigint,
    downvotes bigint
) 
AS $X$
BEGIN
   RETURN QUERY 
    (WITH UP AS
        (SELECT member_id, COUNT(*) AS upvote_number
        FROM upvote
        WHERE action_id = $1
        GROUP BY member_id),
    DOWN AS
        (SELECT member_id, COUNT(*) AS downvote_number
        FROM downvote
        WHERE action_id = $1
        GROUP BY member_id)
    (SELECT m.id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
    (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END )
    FROM member m
        LEFT JOIN UP ON(UP.member_id = m.id)
        LEFT JOIN DOWN ON (DOWN.member_id = m.id)
    )
    ORDER BY m.id);
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION member_and_votes_project (INT) 
   RETURNS TABLE (
    id int4, 
    upvotes bigint,
    downvotes bigint
) 
AS $X$
BEGIN
    RETURN QUERY 
        (WITH UP AS
            (SELECT u.member_id, COUNT(*) AS upvote_number
            FROM upvote u
                JOIN action a ON (a.id = u.action_id)
            WHERE project_id = $1
            GROUP BY u.member_id),
        DOWN AS
            (SELECT d.member_id, COUNT(*) AS downvote_number
            FROM downvote d
                JOIN action a ON (a.id = d.action_id)
            WHERE project_id = $1
            GROUP BY d.member_id)
        (SELECT m.id, (CASE WHEN UP.upvote_number IS NULL THEN 0 ELSE UP.upvote_number END ), 
        (CASE WHEN DOWN.downvote_number IS NULL THEN 0 ELSE DOWN.downvote_number END )
        FROM member m
            LEFT JOIN UP ON(UP.member_id = m.id)
            LEFT JOIN DOWN ON (DOWN.member_id = m.id)
        )
        ORDER BY m.id);
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION index_exists (INT) 
   RETURNS boolean
AS $X$
DECLARE id_num int4;
BEGIN
    FOR id_num IN
        (SELECT id FROM authority)
        UNION
        (SELECT id FROM member)
        UNION
        (SELECT id FROM project)
        UNION
        (SELECT id FROM action)
    LOOP 
        IF (id_num = $1) THEN RETURN TRUE; END IF;
    END LOOP;
    RETURN FALSE;
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION member_exists (INT) 
   RETURNS boolean
AS $X$
DECLARE id_num int4;
BEGIN
    FOR id_num IN
        (SELECT id FROM member)
    LOOP 
        IF (id_num = $1) THEN RETURN TRUE; END IF;
    END LOOP;
    RETURN FALSE;
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION authority_exists (INT) 
   RETURNS boolean
AS $X$
DECLARE id_num int4;
BEGIN
    FOR id_num IN
        (SELECT id FROM authority)
    LOOP 
        IF (id_num = $1) THEN RETURN TRUE; END IF;
    END LOOP;
    RETURN FALSE;
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION project_exists (INT) 
   RETURNS boolean
AS $X$
DECLARE id_num int4;
BEGIN
    FOR id_num IN
        (SELECT id FROM project)
    LOOP 
        IF (id_num = $1) THEN RETURN TRUE; END IF;
    END LOOP;
    RETURN FALSE;
END; $X$ 
LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION action_exists (INT) 
   RETURNS boolean
AS $X$
DECLARE id_num int4;
BEGIN
    FOR id_num IN
        (SELECT id FROM action)
    LOOP 
        IF (id_num = $1) THEN RETURN TRUE; END IF;
    END LOOP;
    RETURN FALSE;
END; $X$ 
LANGUAGE 'plpgsql';

CREATE USER app WITH ENCRYPTED PASSWORD 'qwerty';
GRANT SELECT, INSERT, UPDATE ON TABLE authority, member, project, action, downvote, upvote, 
    action_and_votes_view, member_and_votes_view TO app;
CREATE EXTENSION pgcrypto;
