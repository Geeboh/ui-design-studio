# UI Design Studio v1.2.0

## Live development progress

- A native OMP widget pins phase, gate and coverage counts, progress bars, next action, blockers and the complete Design Server URL below the editor. Pi Tasks retains its own widget.
- A periodic console status command supports hosts without the pinned widget.
- The Design Server displays live workers, tasks, progress history and statistics.

## Artwork and decisions

- The working feed displays contextual thumbnails of artwork and mockups, with full-size viewing and an accumulating version library.
- Guided artistic requests save digest-bound user decisions. Yolo mode records autonomous decisions without waiting for human approval.
- HTML previews are sandboxed and do not run scripts.

## Cleanup and access

- Per-run and all-run cleanup stop owned listeners and remove temporary runtime resources. Design evidence and the artwork library remain intact.
- Successful yolo completion automatically cleans up its server.
- Access URLs authorize inspection and guided approvals. Keep them private. Plain HTTP requires a trusted LAN or an existing protected transport.

## Installation

Download `UI-Design-Studio-OMP-v1.2.0.zip` and its `.zip.sha256` file. Verify the checksum, extract the archive, and follow `README.md`. Existing installations use the documented update procedure. Run `/reload-plugins` in an existing OMP session after updating.

## Verification

The feature passed 142 regression tests and actual installed OMP, browser, artwork, approval and cleanup scenarios on Linux. See the validation record for the tested versions and limits. These checks do not certify other operating systems or public-internet deployment.

## Documentation

- [Changelog](https://github.com/Geeboh/ui-design-studio/blob/v1.2.0/docs/CHANGELOG.md)
- [Installation](https://github.com/Geeboh/ui-design-studio/blob/v1.2.0/docs/INSTALLATION.md)
- [Validation](https://github.com/Geeboh/ui-design-studio/blob/v1.2.0/docs/VALIDATION.md)

The workflow remains reusable across projects. The bundled executable theme tools target CSS and SVG web interfaces. Other UI toolkits require their own adapter and native validation.
