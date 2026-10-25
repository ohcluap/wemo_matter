# Non-GitHub acquisition follow-up

2026-10-24. Public read-only web research and local recording. No GitHub API, repository access, public posts, person-to-person messages, or device requests occurred.

## Update-traffic paper

Primary source: https://people.scs.carleton.ca/~barrera/publications/fps22-bradley.pdf (Bradley and Barrera, Towards Characterizing IoT Software Update Practices).

The paper analyzes a 2019 traffic corpus. It expressly reports no evidence that the Wemo downloaded an update in the captured period. Its unsigned-update discussion derives from an advertised API and earlier research; the authors did not test arbitrary uploads. The S3-download examples do not supply a Wemo 11565 URL. This does not validate an unsigned-image bypass or provide an image acquisition source. The local 11420 binary trace remains stronger evidence for that specific handler implementation.

## Software Freedom Conservancy archive

Primary catalog entry: https://sfconservancy.org/usethesource/candidate/belkin-wls0403-round-1-of-n/

This is WLS040/WLS0403 source material, not F7C063. The inspected catalog contains that Belkin entry; no matching Mini artifact was identified. Its review also reports missing installation instructions. Those observations do not establish Mini bootloader behavior.

The advertised binary download endpoint returned HTML, not firmware. Its form requires a representation that the downloader is assisting SFC as a volunteer in license-compliance evaluation and restricting use to that purpose, with stated FOSS exceptions. This task is device-conversion research, so no such representation was made and no form was submitted. This is not a user-approval request: the different-model artifact is not a demonstrated necessary dependency. No binary was obtained. The HTML is saved locally as artifacts/sfc-binary-page.html.

## Result and limits

Neither new lead supplies exact firmware 11565 or an exact-board bootloader. Search snippets mentioning unsigned images or S3 are not enough to authorize a flash. The stock application/reset investigation remains a candidate architecture, with exact-version and installation access unresolved. Public indexes are incomplete; these negative findings do not prove that a matching artifact cannot exist elsewhere.
