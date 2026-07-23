---

title: "How Instagram Scaled PostgreSQL to Two Billion Users"  
tags:

- postgres
    
- databases
    
- system-design
    
- sharding
    
- scalability  
---
[Source](https://www.youtube.com/watch?v=YLoYcwnqVzM)

PostgreSQL is used in some capacity by major platforms such as Instagram, Reddit, Notion, Heroku, Strava, and Discord. These companies did not stay with a relational database because they were unaware of newer technologies. They evaluated the alternatives and decided that PostgreSQL could continue to work if the surrounding architecture was designed carefully.

Instagram’s history shows that a relational database can scale far beyond the point at which teams are often advised to replace it. PostgreSQL did not solve every distributed systems problem by itself. Instead, Instagram added connection pooling, sharding, caching, precomputed feeds, replication, and custom identifier generation around it.

## The Original Architecture

Instagram launched in 2010 with only three engineers and a deliberately simple architecture. The application ran on Amazon EC2 virtual machines, photos were stored in Amazon S3, and nearly all other information—including user accounts, photo metadata, comments, and likes—was stored in one PostgreSQL database.

This basic design supported approximately 10 million users by 2011. By 2012, when Facebook acquired Instagram for about one billion dollars, the platform had around 27 million users and a PostgreSQL database of roughly 2 TB. The system had reached substantial scale without starting with a complicated distributed architecture.

## The First Bottleneck: Database Connections
![[Pasted image 20260723190145.png|600]]
As the database grew, it approached the memory limits of the largest available EC2 instances and disk I/O became increasingly saturated. However, the first major bottleneck was not simply storage capacity. It was the number of active database connections.

Instagram’s Django application servers repeatedly opened connections to PostgreSQL. Each connection consumed approximately 1.3 MB of memory. With 50 application servers maintaining 30 connections each, the database could receive around 1,500 simultaneous connections. Close to 2 GB of RAM could therefore be consumed before PostgreSQL used that memory for caching, sorting, query planning, or executing useful work.
$$
{\Large
\underbrace{50}_{\substack{\text{application}\\\text{servers}}}
\times
\underbrace{30}_{\substack{\text{connections}\\\text{per server}}}
\times
\underbrace{1.3\ \mathrm{MB}}_{\substack{\text{memory per}\\\text{connection}}}
=
1950\ \mathrm{MB}
\approx 2\ \mathrm{GB}
}
$$
Instagram solved this problem with **PgBouncer**, a lightweight connection-pooling proxy placed between the application and PostgreSQL. Application servers could still create many logical connections, but PgBouncer multiplexed them onto a much smaller pool of real PostgreSQL connections.
![[Pasted image 20260723190305.png|600]]
Instead of maintaining about 1,500 database backends, PostgreSQL could work with a pool of roughly 30 actual connections. This reduced memory overhead and allowed the database to use more resources for query processing. 

> [!important] The broader lesson is that connection management often becomes a visible bottleneck before the database engine reaches its real computational limit.

## Why Instagram Chose Sharding and didn't switch to NoSQL

Connection pooling delayed the problem, but it could not remove the physical limits of a single machine. Eventually, Instagram reached the point where even the largest server could no longer provide enough CPU, memory, storage, and I/O capacity.

A common recommendation at this stage is to replace a relational database with a NoSQL system such as Cassandra or MongoDB. Instagram concluded that its main problem came from scale rather than from an inherent mismatch between its data model and PostgreSQL.

Moving to NoSQL would not remove the need to distribute data horizontally. It would mainly hide sharding behind another abstraction while introducing new operational characteristics, failure modes, and constraints. Instagram therefore kept PostgreSQL and implemented sharding directly.

This decision allowed the team to preserve familiar database behavior, tooling, and operational knowledge while scaling beyond one physical server.

## Choosing the Shard Key
![[Pasted image 20260723191620.png]]
Instagram selected the **user ID** as the shard key. All data associated with a particular user could therefore be stored on the same shard. User-scoped operations remained efficient because the application usually needed to query only one shard.

The disadvantage was that queries involving many users became more difficult. Building a social feed, for example, could require data belonging to users located on many different shards. Instagram accepted this trade-off and solved cross-user workloads at the application layer with caching and precomputed feeds instead of relying on large distributed joins.

The important principle is that every shard key optimizes some access patterns while making others more expensive. A good shard key should match the most common and important queries rather than attempt to make every possible query equally simple.

## Logical Shards and Physical Machines

> [!important]  One of Instagram’s most important architectural decisions was to separate the logical organization of data from the physical servers storing it. Instead of treating one shard as one database machine, Instagram created thousands of **logical shards**, represented as PostgreSQL schemas.

At first, many logical shards could exist on the same physical server. The application used a **mapping** that associated every logical shard with its current physical location. This extra layer of indirection made future scaling much easier.

Example of a mapping table:

| logical_shard_id | physical_node | host    | replica_lag | size_gb | last_migrated | status  | owner_team |
|------------------|---------------|---------|-------------|---------|---------------|---------|------------|
| 0000             | N0            | db-0.1g | 12 ms       | 47      | —             | healthy | feed       |
| 0001             | N0            | db-0.1g | 12 ms       | 48      | —             | healthy | feed       |
| —                | —             | —       | —           | —       | —             | —       | —          |
| 1920             | N7            | db-7.1g | 31 ms       | 62      | moved 09-12   | healthy | media      |
| —                | —             | —       | —           | —       | —             | —       | —          |

When a server approached its storage or performance limits, Instagram did not need to redesign the shard key or repartition the complete dataset. The process was more limited:
![[Pasted image 20260723192422.png]]
1. Copy selected logical shards to another machine using streaming replication.
2. Update the shard-to-server mapping.
3. Redirect application traffic to the new location.

The logical identity of each shard remained unchanged even though its physical placement moved. This avoided a full resharding operation whenever new hardware was added and made individual shards movable units of data rather than permanent parts of one server.

## Generating Unique IDs Across Shards

Sharding created another problem: ordinary auto-incrementing identifiers were no longer globally unique. Two shards could independently generate the same numeric ID. A centralized sequence generator could solve collisions, but it would introduce coordination overhead and a potential single point of failure.

Instagram considered several alternatives. **UUIDs** provided uniqueness but were considered too large and not naturally sortable by creation time. **Flickr-style ticket servers** depended on centralized infrastructure, while Twitter’s **Snowflake approach** required a separate service.

Instagram instead implemented a *Snowflake-style ID generator* directly inside PostgreSQL. Each identifier was stored as a 64-bit integer with the following structure:

|Bits|Purpose|
|--:|---|
|41|Timestamp in milliseconds|
|13|Logical shard identifier|
|10|Sequence number within the same shard and millisecond|

**The timestamp made identifiers roughly sortable by creation time.** The shard identifier prevented different logical shards from generating the same value, while the sequence number allowed multiple IDs to be created within one millisecond on the same shard.

Because the logic was implemented as a PostgreSQL function, every shard could generate globally unique identifiers without contacting an external coordination service. 

## PostgreSQL Features Used for Efficiency

Instagram also relied on several PostgreSQL features that improved storage efficiency and supported downstream systems.

### Partial Indexes

A partial index contains only rows that satisfy a condition. For example, an index could include only photos created during the last 30 days instead of indexing the complete historical table. If most application traffic concerns recent data, the resulting index can be much smaller and faster than a full index.

### Functional Indexes

A functional index stores the result of an expression rather than the full original column value. If an application frequently searches using only the first eight characters of a long token, PostgreSQL can index that shortened expression. This reduces index size while preserving efficient lookups for the actual query pattern.

### Logical Replication

Logical replication streams inserts, updates, and deletes to downstream consumers. According to the video, this can be used to keep systems such as search indexes or caches synchronized in near real time. For workloads that only require database changes to be propagated elsewhere, it can serve as a simpler alternative to a more complex event-streaming setup.

## Main Lessons

Instagram kept a single PostgreSQL database until it had tens of millions of users. This allowed a very small engineering team to focus on the product rather than operating a distributed data platform too early.

When horizontal scaling became unavoidable, the team separated logical shards from physical machines so that capacity could be added without repeatedly redesigning data placement. Connection pooling was introduced before replacing the database, and globally unique identifiers were generated independently on every shard.

The system also avoided forcing every query into a distributed relational model. Difficult cross-user workloads were handled with application-level caching and precomputed results. PostgreSQL remained responsible for the workloads it handled well, while surrounding components addressed the problems created by scale.

> [!important] The broader conclusion is that the database is rarely the only bottleneck. Scalability depends on the architecture around it: how connections are managed, how data is partitioned, how identifiers are generated, how read patterns are cached, and how changes are propagated to other systems.

## Key Takeaways

1. Start with a simple PostgreSQL architecture and delay sharding until a real capacity limit appears.
    
2. Use connection pooling because thousands of PostgreSQL connections can consume substantial memory.
    
3. Choose a shard key that keeps the most commonly accessed related data together.
    
4. Accept that every shard key makes some queries easier and others more difficult.
    
5. Separate logical shards from physical database machines so shards can be moved independently.
    
6. Use Snowflake-style IDs to avoid collisions and centralized coordination.
    
7. Apply partial and functional indexes to real access patterns instead of indexing unnecessary data.
    
8. Use replication when database changes need to be delivered to downstream systems.
    
9. Spend the team’s complexity budget only on problems that cannot be solved effectively with existing infrastructure.
    
10. Treat scaling as an architectural problem around the database, not as an automatic reason to abandon PostgreSQL.