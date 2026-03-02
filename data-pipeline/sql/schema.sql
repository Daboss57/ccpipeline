create table if not exists schools (
  school_id text primary key,
  name text not null,
  system text not null,
  term_system text not null
);

create table if not exists majors (
  major_id text primary key,
  school_id text not null references schools(school_id),
  major_key text not null,
  major_name text not null,
  department text,
  total_units integer not null,
  source jsonb
);

create table if not exists courses (
  school_id text not null references schools(school_id),
  course_id text not null,
  course_name text not null,
  units integer not null,
  department text,
  catalog_level text,
  description text,
  offered_terms jsonb not null,
  primary key (school_id, course_id)
);

create table if not exists course_offerings (
  school_id text not null references schools(school_id),
  course_id text not null,
  offered_terms jsonb not null,
  primary key (school_id, course_id)
);

create table if not exists exam_credit_policies (
  school_id text not null references schools(school_id),
  exam_type text not null,
  exam_name text not null,
  min_score integer not null,
  units_granted integer not null,
  courses_satisfied jsonb not null,
  ge_areas_satisfied jsonb not null,
  source_name text,
  source_url text,
  policy_year text,
  primary key (school_id, exam_type, exam_name)
);

create table if not exists major_requirements (
  university_id text not null references schools(school_id),
  major_id text not null references majors(major_id),
  requirement_id text primary key,
  course_id text not null,
  course_name text not null,
  units integer not null,
  type text not null,
  term_offerings jsonb not null,
  source_name text,
  source_url text,
  policy_year text
);

create table if not exists course_prerequisites (
  university_id text not null references schools(school_id),
  course_id text not null,
  prerequisite_course_id text not null,
  min_grade text not null,
  primary key (university_id, course_id, prerequisite_course_id)
);

create table if not exists igetc_courses (
  cc_id text not null references schools(school_id),
  igetc_area text not null,
  course_id text not null,
  course_name text not null,
  units integer not null,
  source_url text,
  policy_year text,
  primary key (cc_id, igetc_area, course_id)
);

create table if not exists assist_articulations (
  cc_id text not null references schools(school_id),
  university_id text not null references schools(school_id),
  major_id text not null references majors(major_id),
  cc_course_id text not null,
  satisfies_requirement_id text not null,
  source jsonb,
  primary key (cc_id, university_id, major_id, cc_course_id, satisfies_requirement_id)
);
