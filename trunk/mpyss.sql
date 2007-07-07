
create table revision (
    rv_repo_url varchar(256) not null,
    rv_number integer not null,
    rv_author varchar(128),
    rv_timestamp timestamp not null,
    rv_comment varchar(102400) not null,
    primary key(rv_repo_url, rv_number)
);

create index revision_url_author_i on revision (rv_repo_url, rv_author);
create index revision_url_timestamp_i on revision (rv_repo_url, rv_number);

create table changed_path (
    rv_repo_url varchar(256) not null,
    rv_number integer not null,
    cp_path varchar(4096) not null,
    cp_action varchar(1) not null,
    primary key (rv_repo_url, rv_number, cp_path),
    foreign key (rv_repo_url, rv_number) references revision (rv_repo_url, rv_number)
);

create index changed_path_url_i on changed_path (rv_repo_url);

create table calendar (
    calendar_type varchar(128) not null,
    timestamp timestamp not null,
    year integer not null,
    month integer not null,
    day integer not null,
    hour integer not null,
    minute integer not null,
    second number not null
);

create index calendar_timestamp_i on calendar(timestamp);
create index calendar_type_i on calendar(calendar_type);
