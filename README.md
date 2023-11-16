# Winjhin

This is Winjhin, a third-party account statistics and match history website for the game League of Legends. The project was written entirely by me, from start to finish, with the exception of any images that were taken from the game asset tarball that the game's developer provides.
The app was written primarily in Python, and utilizes Flask. The app also uses a wrapper to communicate with the Riot Games API called 'pantheon'.

While the app is fully-functioning in its current state, it cannot be readily exported and used, as an API key is required for it to actually perform its purpose. Unfortunately, the API keys that are given out by the developer
are available only to those who go through a rigorous application process, and they have to be refreshed every 24 hours. Because of this, the only way I can show how the website works is through a demonstration, which I will link to here:
https://www.youtube.com/watch?v=Z2iW6nTvWss

Challenges in development:
- Development test API key is heavily rate-limited, so storing considerable amounts of account data for testing had to be done over a long period of time, and could not be done on more than a couple of accounts.
- Keys used in the JSON data sent by the API have names that reference the game's current patch/version, so even some static files in the app have to constantly update, along with the game.
- Placing value player performance is highly difficult and often subjective, so the grading criteria is far from perfect.
- Some particular bits of the information returned by the API were consistently inaccurate, so I had to write a custom algorithm for them, instead.
