const http = require('http');
const fs = require('fs');
const url = require('url');

const debugmode = true;

http.createServer(function(request, response) {
	var body = "";
	request.on('readable', function() {
		var buffer = request.read();
		if (buffer) { body += buffer; }
	});
	request.on('end', function() {
		if (debugmode) { console.log(request.method, request.url, "**", body, "**"); }
		requestHandlerFactory(request.url, executeHandler);
		function executeHandler(requestHandler) {
			requestHandler(request.method.toLowerCase(), request.url.toLowerCase(), body, response);
		}
	});
}).listen(80);

console.log('running - server');

function fileHandler(method, page, body, response) {
	console.log("fileHandler: " + page);
	var pathname = url.parse(page).pathname;
	if (pathname == '/') {
		pathname = '/index.html';
	}
	pathname = '.' + pathname;
	console.log("fileHandler:path: " + pathname);
	fs.readFile(pathname, function(err, data) {
		if (err) {
			response.writeHead(404, {'Content-Type': 'text/html'});
			response.end();
		}
		else {
			var mime = 'text/html';
			switch(pathname.substr((~-pathname.lastIndexOf(".") >>> 0) + 2))
			{
				case 'svg':
					mime = 'image/svg+xml';
					break;
				case 'css':
					mime = 'text/css';
					break;
				case 'js':
					mime = 'application/javascript';
					break;
			}
			response.writeHead (200, {'Content-Type': mime});
			response.write (data);
			response.end();
		}	
	});
}

function pageHandler(method, page, body, response) {
	console.log("pageHandler: " + page);

	var pathname = url.parse(page).pathname;
	pathname = '.' + pathname;

	fs.readFile(pathname, "utf8", function(err, data) {
		if (err) {
			response.writeHead(404, {'Content-Type': 'text/html'});
			response.end();
		}
		else {
			response.writeHead (200, {'Content-Type': 'text/html'});
			response.write (data);
			response.end();
		}	
	});
};

function nullHandler(method, page, body, response) {
	console.log("nullhandler:" + page);
	response.writeHead(500);
	response.end();	
	return;
};

function requestHandlerFactory(url, callback) {
	if (url.toLowerCase().endsWith('.html')) {
		callback(pageHandler);
		return;
	}

	return callback(fileHandler);
}
