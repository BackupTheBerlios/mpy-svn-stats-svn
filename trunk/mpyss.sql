
create table revision (
    rv_repo_url varchar(256) not null,
    rv_number integer not null,
    rv_author varchar(128),
    rv_timestamp timestamp not null,
    rv_comment varchar(102400) not null,
    primary key(rv_repo_url, rv_number)
);

create table changed_path (
    rv_repo_url varchar(256) not null,
    rv_number integer not null,
    cp_action varchar(1) not null,
    cp_path varchar(4096) not null,
    foreign key (rv_repo_url, rv_number) references revision (rv_repo_url, rv_number)
);

