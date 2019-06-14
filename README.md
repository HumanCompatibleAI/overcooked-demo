# Overcooked Demo
A web application where humans can play Overcooked with trained AI agents.

## Installation

First, install `node` and `npm`, and ensure that you have set up the [overcooked-js repository](https://github.com/markkho/overcooked-js).

Then, at the top-level directory:

    overcooked-demo $ npm install
    overcooked-demo $ npm link /path/to/overcooked-js/
    overcooked-demo $ npm run build

Annoyingly, some underlying library introduces a bug into the compiled code. To fix it, open the file `static/js/demo/demo.js` (which should have been created by the npm build command) and change the line

    exports.fetch = fetch;

to

    exports.fetch = window.fetch.bind(window);

At this point the code should be ready to run. Start the server with

    overcooked-demo $ node index.js

at which point you should be able to load the website in any browser by going to [http://localhost:8766](http://localhost:8766).
