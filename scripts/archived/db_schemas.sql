-- https://dbdiagram.io/d

-- v0 (normalized)
Table topics {
  id int [not null, unique]
  name varchar [pk, not null, unique]
}

Table feeds {
  id int [not null, unique]
  topic_id int [pk, ref: > topics.id]
  name varchar [pk]
}

Table urls {
  id int [not null, unique]
  url varchar [pk]
}

Table posts {
  feed_id int: [pk, ref: > feeds.id]
  url_id int: [pk, ref: > urls.id]
}

-- v1 (denormalized)
Table posts {
  topic_name varchar [pk]
  feed_name varchar [pk]
  url varchar [pk]
}

-- v2 (denormalized hashes)
Table posts {
  topic_hash int [pk]
  feed_hash int [pk]
  url_hash int [pk]
}