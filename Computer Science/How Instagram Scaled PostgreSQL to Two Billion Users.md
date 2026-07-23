---
tags:
  - postgres
  - databases
  - system-design
  - sharding
  - scalability
---
source: https://www.youtube.com/watch?v=YLoYcwnqVzM

PostgreSQL is used in some capacity by large platforms such as Instagram, Reddit, Notion, Heroku, Strava, and Discord. The important point is not that these companies were unaware of newer database technologies, but that they evaluated their requirements and chose to keep a mature relational database at the center of their systems. Instagram’s history demonstrates that a relational database can be pushed far beyond the scale at which engineers are often advised to replace it. The database itself was not treated as an isolated product that had to solve every problem automatically. Instead, Instagram changed the architecture around PostgreSQL by introducing connection pooling, application-level sharding, caching, precomputed data, replication, and custom identifier generation.

## From a Single Database to the First Scaling Limits

Instagram launched in 2010 with a team of only three engineers and a deliberately simple architecture. The application ran on Amazon EC2 virtual machines, photos were stored in Amazon S3, and nearly all other information—including accounts, photo metadata, comments, and likes—was stored in one PostgreSQL database. This basic design was enough to support approximately 10 million users by 2011. By 2012, when Facebook acquired Instagram for about one billion dollars, the service had around 27 million users and a PostgreSQL database of roughly 2 TB. The system had reached substantial scale without beginning with a complicated distributed architecture.

The first serious limitation was not simply the amount of stored data. As the database approached the memory capacity of the largest available EC2 instances and disk I/O became increasingly saturated, the number of database connections also became a major problem. Instagram’s Django application servers repeatedly opened connections to PostgreSQL, and every connection consumed approximately 1.3 MB of memory. With 50 application servers maintaining 30 connections each, around 1,500 database connections could consume close to 2 GB of RAM before PostgreSQL used that memory for caching, sorting, query planning, or other productive work.

Instagram addressed this bottleneck with **PgBouncer**, a lightweight connection-pooling proxy placed between the application and PostgreSQL. Application servers could still create many logical connections, but PgBouncer multiplexed them onto a much smaller pool of actual PostgreSQL connections. Instead of forcing the database to maintain about 1,500 separate backend processes, a pool of roughly 30 real connections could serve the application traffic. This reduced memory overhead and allowed PostgreSQL to use more of the machine’s resources for executing queries. The broader lesson is that connection management often becomes a visible bottleneck before the database engine itself has reached its true processing limit.

## Choosing Sharding Instead of Replacing PostgreSQL

Connection pooling delayed the problem but could not remove the physical limits of a single machine. Eventually, Instagram reached the point where even the largest available server could no longer provide enough CPU, memory, storage, and I/O capacity. A common recommendation at this stage is to replace the relational database with a NoSQL system such as Cassandra or MongoDB. Instagram concluded, however, that its main difficulty came from scale rather than from an inherent mismatch between its data model and PostgreSQL.

Moving to NoSQL would not eliminate the need to distribute data horizontally. It would mainly move the sharding logic behind another abstraction and introduce a new set of operational characteristics, failure modes, and constraints. Instagram therefore kept PostgreSQL and implemented sharding directly. This decision preserved the database behavior, tooling, and operational knowledge the engineering team already understood while allowing the system to grow beyond one physical server.

The chosen shard key was the **user ID**. Data associated with a particular user could therefore be placed on the same shard, making user-scoped operations efficient because the application usually needed to query only one shard. The disadvantage was that queries involving many users became harder. Building a social feed, for example, could require data belonging to users located on many different shards. Instagram accepted this trade-off and handled cross-user workloads at the application layer with caching and precomputed feeds rather than forcing the relational database to perform large distributed joins across all shards.

## Separating Logical Shards from Physical Machines

One of the most important architectural choices was to separate the logical organization of data from the physical servers that stored it. Instead of making one shard equal to one database machine, Instagram created thousands of **logical shards**, represented as PostgreSQL schemas. At first, many of these logical shards could live together on the same physical server. The application used a mapping that associated each logical shard with its current physical location.

This additional layer of indirection made future scaling much easier. When a physical database server approached its storage or performance limits, Instagram did not need to redesign the shard key or repartition the entire dataset. Some logical shards could be copied to another machine through streaming replication, the application’s shard mapping could be updated, and traffic could then be directed to the new location. The logical identity of the shards remained stable even though their physical placement changed.

This design avoided a painful full resharding operation every time new hardware was added. Capacity expansion became primarily a matter of moving a manageable number of logical units and changing configuration. It also allowed unevenly growing shards to be redistributed independently. The key principle is that a shard should be a movable logical unit rather than a permanent synonym for a specific server.

## Generating Unique IDs Across Shards

Sharding created another problem: normal auto-incrementing database identifiers were no longer globally unique. Two shards could independently generate the same numeric ID, and a centralized sequence generator would introduce coordination overhead and a potential single point of failure. Instagram considered several alternatives. UUIDs provided uniqueness but were regarded as too large and not naturally sortable by creation time. Flickr-style ticket servers depended on dedicated centralized infrastructure, while Twitter’s Snowflake design required a separate service.

Instagram instead implemented a Snowflake-style identifier generator directly inside PostgreSQL. Each ID was stored as a 64-bit integer composed of three parts:

|Bits|Purpose|
|--:|---|
|41|Timestamp in milliseconds|
|13|Logical shard identifier|
|10|Sequence number within the same shard and millisecond|

The timestamp made identifiers roughly sortable by creation time, the shard identifier prevented different logical shards from generating the same value, and the sequence component allowed multiple IDs to be created within one millisecond on the same shard. Because the logic was implemented as a PostgreSQL function, every shard could generate globally unique identifiers without contacting an external coordination service. The video presents this as a pattern later used in systems such as Discord and Slack.

## PostgreSQL Features Used for Efficiency

Instagram also benefited from PostgreSQL features that can reduce index size and support data movement. **Partial indexes** store entries only for rows that satisfy a condition. For example, an index could cover only photos created during the last 30 days instead of indexing the full historical table. When most application traffic concerns recent data, this can produce an index that is much smaller and faster than a complete index over every row.

**Functional indexes** store the result of an expression rather than the original full column value. If an application frequently searches using only the first eight characters of a long token, PostgreSQL can index that shortened expression. This preserves efficient lookups for the actual access pattern while reducing the amount of index storage required.

The third highlighted feature is **logical replication**, which streams inserts, updates, and deletes to downstream consumers. The video describes it as a way to keep systems such as search indexes or caches synchronized in near real time, potentially avoiding a more complex event-streaming setup for workloads that only require database changes to be propagated elsewhere.

## The Complexity Budget and “Boring Technology”

The architectural story is tied to the idea that every engineering team has a limited **complexity budget**. Introducing a new database or infrastructure platform requires engineers to learn its behavior, understand failure scenarios, build monitoring and operational procedures, and hire people with the relevant expertise. A mature technology such as PostgreSQL, Linux, or Memcached already has extensive documentation, known operational patterns, and a large pool of experienced engineers. Its adoption cost is therefore lower than that of a specialized technology whose advantages may not be necessary for the current problem.

This does not mean that specialized databases should never be used. The video argues that they are justified when the system encounters a genuinely different problem, such as vector search or planet-scale graph traversal. They should not be introduced merely because the application has become popular or because a relational database has reached the capacity of one server. Instagram’s approach was to identify each specific bottleneck and solve it directly: PgBouncer addressed connection overhead, sharding addressed single-machine limits, caching and precomputation addressed cross-user queries, and a custom 64-bit ID scheme addressed globally unique identifier generation.

## Instagram’s Current Architecture and Main Lessons

The techniques described above are foundational lessons from Instagram’s scaling journey, not a claim that its entire modern architecture still consists of the same PostgreSQL shards. According to the video, by 2026 Instagram’s social graph had been integrated into Meta’s internal infrastructure and was handled by **TAO**, a distributed system designed for graph workloads. This change is consistent with the broader principle presented in the video: keep mature general-purpose technology while it fits the problem, and introduce specialized infrastructure when the workload becomes fundamentally different.

The central lesson is to avoid premature distribution. Instagram kept a single PostgreSQL database until it had tens of millions of users, allowing the small engineering team to focus on the product instead of operating a complex distributed data platform. When horizontal scaling became unavoidable, the team separated logical shards from physical nodes so that capacity could be added without repeatedly redesigning data placement. Connection pooling was introduced before replacing the database, and globally unique, time-ordered identifiers were generated independently on every shard. The system did not attempt to make every query a distributed relational operation; difficult cross-user workloads were handled with application-level caching and precomputed results.

In this view, the database is rarely the only bottleneck. Scalability depends on the surrounding architecture: how connections are managed, how data is partitioned, how identifiers are generated, how read patterns are cached, and how changes are delivered to downstream systems. Instagram’s experience shows that PostgreSQL can remain useful at enormous scale when engineers understand its limits and add complexity only where the workload requires it.

## Key Takeaways

1. Start with a simple PostgreSQL architecture and delay sharding until a real capacity limit appears.
    
2. Use connection pooling because thousands of PostgreSQL connections can waste substantial memory.
    
3. Choose a shard key that keeps the most common related data together; Instagram used the user ID.
    
4. Accept that a shard key optimizes some queries while making others more difficult.
    
5. Separate logical shards from physical database machines so shards can be moved without redesigning the entire dataset.
    
6. Use independently generated Snowflake-style IDs to avoid collisions and centralized coordination.
    
7. Apply partial and functional indexes to the actual access patterns instead of indexing more data than necessary.
    
8. Use replication to propagate database changes to downstream systems when that is sufficient for the workload.
    
9. Spend the team’s complexity budget only on problems that cannot be solved effectively with existing infrastructure.
    
10. Treat scaling as an architectural problem around the database, not as an automatic reason to abandon PostgreSQL.