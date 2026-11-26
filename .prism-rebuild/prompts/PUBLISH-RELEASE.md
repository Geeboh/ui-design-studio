# Publish a verified PRISM release — explicit authority required

Use this prompt only when you intend to authorize publication of the already verified release candidate. The implementation goal does not run it automatically.

## Prompt to send

Publish the verified PRISM Studio release candidate from this repository according to its release policy. I authorize pushing the reviewed feature branch, creating or updating its PR, and publishing the matching version tag/release and verified artifacts once the required checks and branch policy permit it. Do not force-push, delete history or bypass required reviews/checks. Do not merge the default branch unless I have explicitly authorized that merge in this session.

Verify the remote owner/repository, current source commit, release version, immutable artifact digests and up-to-date release evidence before any write. Use the existing authenticated Git/GitHub tooling. Avoid printing credentials. If release policy requires a default-branch merge that is not authorized, complete the PR and stop at that concrete remaining step; do not claim publication.

After the authorized writes, verify the remote commit/tag and release asset names/digests. Report their actual URLs and observed status. A prepared local archive or successful upload request alone is not proof that the published release is correct.
