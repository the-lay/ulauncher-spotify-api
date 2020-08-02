ulauncher-spotify-api
--------------------------
[ulauncher](https://github.com/Ulauncher/Ulauncher) extension that provides Spotify controls through WebAPI.

![Demo gif](demo.gif)

*Note: some playback features are allowed only for Spotify Premium subscribers (see `Known issues` below).*

Motivation
--------------------------
There's a great Ulauncher extension [pywkm/ulauncher-spotify](https://github.com/pywkm/ulauncher-spotify).
However, ulauncher-spotify uses dbus to control Spotify, exposing very limited number of Spotify features to user.

In contrast, this extension makes use of Spotify's [Web API](https://developer.spotify.com/documentation/web-api/)
through which it is possible to use almost all Spotify features. The aim is to provide direct access to most features
that make sense for a command runner.

Installation
--------------------------
For now, you need to manually get your own Spotify Client ID and Client Secret in Dev Dashboard (and write it to secrets.py)
Eventually, when spotipy library supports PKCE, I will be able to distribute encrypted id and secret.

Ulauncher does not support extension's `requrements.txt`,
although [it's in the roadmap](https://github.com/Ulauncher/Ulauncher/issues/273).
For now, you have to manually install [spotipy](https://github.com/plamere/spotipy/)
on your systems Python installation. For example with PIP: `pip3 install spotipy`.

Next, you have to go to Ulauncher's Preferences, press Add extension and enter link to this repository:
[TODO](TODO)

Extension's default keyword is `sp`. When you use the extension for the first time, you will have to
go through OAuth authentication and allow access to your Spotify account.
After that,you will be able to use the extension.

*Note: if you ever want to revoke extension's access, you can do so in the
[Apps tab of your Spotify settings](https://www.spotify.com/account/apps/).*


Currently implemented
--------------------------
- Authenticate the user with the Spotify API and automatically refresh access token when expired (`sp` - first run or
when access token is expired)
- Playback functionality: play, pause, next/previous track (`sp` - default menu)
- Show current playback
- Error handling, gracefully handling most of the API errors
- Initiate playback on different devices (if not playing)
- Switch playback between devices (`sp switch`)
- Change repeat state (`sp repeat`)
- Change shuffle state (`sp shuffle`)
- Search for track/album/artist/playlist (`sp album/track/artist/playlist search_query`)
- Search without specifying a type (`sp search search_query`)
- Download images to cache folder and show them in search (and clear cache on extension exit)
- Alt-enter to add track to queue instead of playing now


Feature roadmap
--------------------------
- [PKCE authentication](https://developer.spotify.com/documentation/general/guides/authorization-guide/#authorization-code-flow-with-proof-key-for-code-exchange-pkce)
 once Spotipy library officially supports it
- Add aliases/shortcuts (for example `sp song` or `sp s` can be the same as `sp track`)
- Podcasts functionality (`sp podcast`)
- Start a radio based on currently playing track (`sp radio`)

If you have any suggestions or feel that something is missing, please [open a new issue](TODO).


Known issues
--------------------------
- Spotipy's authentication workflow sets up a tiny web server to accept back Spotify's access token.
By default port 8080 is used. If it is taken, authentication will probably crash.

- Unfortunately, Spotify does not provide API access for free users for the following actions:
  - Next track (Skip User’s Playback To Next Track)
  - Previous track (Skip User’s Playback To Previous Track)
  - Start/resume playback (Start/Resume a User's Playback)
  - Pause playback (Pause a User's Playback)
  - Set repeat mode (Set Repeat Mode On User’s Playback)
  - Switch device (Transfer a User's Playback)
  - Scroll track (Seek To Position In Currently Playing Track)
  - Set volume (Set Volume For User's Playback)
  - Toggle shuffle (Toggle Shuffle For User’s Playback)
  - Add to queue (Add an item to the end of the user's current playback queue)
  
  You will see 403 errors if you try to use those as a free user. 