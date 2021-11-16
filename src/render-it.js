var system = require('system');
var url = system.stdin.readLine();

var webpage = require('webpage');
var page = webpage.create();
page.open(url, function()
{
    page.viewportSize = {'width': 488, 'height': 2048};
    page.evaluate(function()
    {
        document.body.style.background = 'transparent';
        document.body.style.color = 'white';
        document.body.style.width = '50%';
        document.body.style.transformOrigin = 'top left';
        document.body.style.transform = 'scale(2)';
        document.body.style.overflow = 'hidden';
        document.body.style.WebkitTextStrokeWidth = '0.5px';
    });
    page.viewportSize = JSON.parse(page.evaluate(function()
    {
        var r = new Range();
        r.setStart(document.body, 0);
        r.setEnd(document.body, document.body.childNodes.length);
        var bcr = r.getBoundingClientRect();
        return JSON.stringify({'width': bcr.right+8, 'height': bcr.bottom+8});
    }));
    console.log(page.renderBase64('PNG'));
    console.log(JSON.stringify(page.viewportSize));
    phantom.exit();
});
