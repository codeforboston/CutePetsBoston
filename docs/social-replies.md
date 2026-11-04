# Social reply engine

`reply_inbox.py` reads direct comments on our saved Bluesky, Mastodon, and
Instagram posts. It previews responses from `social_replies/replies.json`.
No LLM is used. Every phrase can appear on either a cat or dog post.

```sh
uv run python reply_inbox.py --database database.json
```

The **Audit social replies** action uses the latest production database artifact
and repository Instagram credentials. It only reads comments and uploads
`reply-inbox.json`, containing the comments, platform coverage, read errors, and
proposed responses. It cannot send replies. Posting, metrics, and Pages workflows
are unaffected.

The audit samples up to 30 posts per platform from the last 30 days, checking
posts with recorded comments first. Counts describe the sample, not the entire
account history. Platform thread endpoints can return only part of a large
conversation. Instagram reads up to five pages per post; its token needs comment
access, which publishing permission alone may not provide. A read error is
reported as an error, never treated as an empty inbox.

## Reply policy

- About one in three eligible comments, chosen consistently by comment ID.
- Up to five responses per UTC day across all platforms; configurable with
  `--rate` and `--daily-cap`.
- At most one proposed response per pet post; saved history prevents later
  runs from responding again in that thread.
- Skip our own comments, known bots, comments already answered by us, and
  comments older than seven days.
- Skip questions, links, long comments, and basic adoption/grief/problem
  keywords. This is a simple filter, not an understanding of the conversation;
  review the preview before enabling real sending.
- The shared pool deliberately includes woofs, meows, purrs, and emojis.

## Sending later

Real sending requires explicitly running `reply_inbox.py --send`. The audit
workflow does not expose this option. Use the intended account's platform
credentials and a persistent `--state` file; keep that file between runs.

The state reserves a comment before the network request. A failed or uncertain
send remains reserved for manual review rather than automatically retrying and
possibly duplicating a reply. Invalid state fails loudly. Do not schedule real
replies until durable state storage and the preview results have been reviewed.

API references: [Bluesky replies](https://docs.bsky.app/docs/tutorials/creating-a-post#replies),
[Mastodon contexts and replies](https://docs.joinmastodon.org/methods/statuses/),
[Instagram comment moderation](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/comment-moderation/).
