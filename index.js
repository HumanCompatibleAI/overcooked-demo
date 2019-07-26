var express = require('express');
var app = express();
app.set('view engine', 'ejs');
app.use(express.static('static'))

app.get('/', function(req, res) {
    res.render("demo");
});

app.get('/replay', function(req, res) {
    res.render("replay");
});

app.get('/instructions', function(req, res) {
    res.render("instructions");
});

app.listen(8766);
