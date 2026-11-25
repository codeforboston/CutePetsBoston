# CutePetsBoston

CutePetsBoston shares shelter pets on social media and reports on those posts and the pets' adoption statuses.

## Language

**Pet**:
An animal listed by a shelter or adoption source. A pet can appear in multiple social posts; its name is a display label, not its identity.

**Published post**:
A successfully published social media message about a pet on one platform. Multiple published posts can refer to the same pet.
_Avoid_: Pet, when counting social media messages

**Posted pet**:
A distinct pet with at least one successfully published post, regardless of how many platforms published it. A failed posting attempt alone does not make a pet a posted pet.

**Pet archive**:
The lasting collection of previously posted pets and their tracked adoption statuses, without an age cutoff. It includes pets with no confirmed adoption as well as adopted pets.

**Engagement snapshot**:
The cumulative likes, reposts, and comments reported for one published post at an observation time. Successive snapshots are repeated measurements, not separate amounts of engagement to add together.

**Engagement summary**:
The latest saved engagement snapshot for a published post after its collection window closes. It represents the last observed counts, not guaranteed lifetime totals.

**Reported adoption status**:
A pet's disposition as reported by its adoption source at the time it was observed, such as Available, Pending, or Adopted. An Adopted report does not establish that a CutePetsBoston post caused the adoption.

**Status observation time**:
The time the adoption source last successfully reported the saved status. For the final Adopted state, this is when adoption was first observed, not the actual adoption date.

**Adopted**:
A final tracked state reached when the adoption source explicitly reports the pet as adopted. Once reached, this state is preserved even if the source later changes its report.

**Status lookup**:
An attempt to retrieve a pet's reported adoption status. An unavailable or missing result is not evidence that the pet was adopted.

**Missing source record**:
A lookup that successfully reaches the adoption source but returns no matching animal record. A timeout or service failure does not establish that a source record is missing.
