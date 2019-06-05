CREATE TABLE authority (
    id bigint NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE downvote (
    id bigint NOT NULL, 
    member_id int4 NOT NULL, 
    action_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE member (
    id bigint NOT NULL, 
    password char(128) NOT NULL, 
    last_activity timestamp NOT NULL, 
    leader bool DEFAULT 'false' NOT NULL, 
    dead bool DEFAULT 'false' NOT NULL, 
    upvotes int4 DEFAULT 0 NOT NULL, 
    downvotes int4 DEFAULT 0 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE project (
    id bigint NOT NULL, 
    authority_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE protest (
    id bigint NOT NULL, 
    project_id int4 NOT NULL, 
    member_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE support (
    id bigint NOT NULL, 
    project_id int4 NOT NULL, 
    member_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
CREATE TABLE upvote (
    id bigint NOT NULL, 
    member_id int4 NOT NULL, 
    action_id int4 NOT NULL, 
    PRIMARY KEY (id)
);
ALTER TABLE project ADD CONSTRAINT authority_owns_project FOREIGN KEY (authority_id) REFERENCES authority (id);
ALTER TABLE downvote ADD CONSTRAINT member_can_downvote FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE upvote ADD CONSTRAINT member_can_upvote FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE protest ADD CONSTRAINT member_creates_protest FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE support ADD CONSTRAINT member_creates_support FOREIGN KEY (member_id) REFERENCES member (id);
ALTER TABLE protest ADD CONSTRAINT project_has_protest FOREIGN KEY (project_id) REFERENCES project (id);
ALTER TABLE support ADD CONSTRAINT project_has_support FOREIGN KEY (project_id) REFERENCES project (id);
ALTER TABLE downvote ADD CONSTRAINT protest_has_downvote FOREIGN KEY (action_id) REFERENCES protest (id);
ALTER TABLE upvote ADD CONSTRAINT protest_has_upvote FOREIGN KEY (action_id) REFERENCES protest (id);
ALTER TABLE downvote ADD CONSTRAINT support_has_downvote FOREIGN KEY (action_id) REFERENCES support (id);
ALTER TABLE upvote ADD CONSTRAINT support_has_upvote FOREIGN KEY (action_id) REFERENCES support (id);
CREATE USER testapp WITH ENCRYPTED PASSWORD 'testpass';
--GRANT ALL PRIVILEGES ON  DATABASE test TO testapp ;