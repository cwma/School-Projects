/** 
 * @author: Chia Wei Meng Alexander
 * Matric: A0112937E
 * 
 * WebServer.java
 * Classes: HttpCode, Template, Router, HttpRequest, HttpResponse, Worker, WebServer
 * 
 */

import java.net.*;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.InputMismatchException;
import java.util.List;
import java.util.Map;
import java.io.*;


/**
 * @enum HttpCode
 * Is an enum used to represent the supported Http response codes by this WebServer.
 * Pretty self explanatory
 */
enum HttpCode{
	_200 ("200 OK"), 
	_201 ("201 Created"),
	_301 ("301 Moved Permanently"),
	_400 ("400 Bad Request"),
	_403 ("403 Forbidden"),
	_404 ("404 Not Found"),
	_500 ("500 Internal Server Error");

	private String desc;
	
	private HttpCode(String desc){
		this.desc = desc;
	}
	
	@Override
	public String toString(){
		return desc;
	}
}

/**
 * @class Template
 *	static class used to render default page views for the WebServers responses.
 */
class Template {
	
	//template strings
	private static final String _400 = "<html><h1> 400 Bad Request </h1><body><p> GET and POST requests only </p>{footer}</body></html>";
	private static final String _404 = "<html><h1> 403 Forbidden </h1><body><p> You are not allowed to be here!</p>{footer}</body></html>";
	private static final String _403 = "<html><h1> 404 File not found </h1><body><p> Are you sure you are looking in the right place?</p>{footer}</body</html>";
	private static final String _500 = "<html><h1> 500 Internal Server Error </h1><body><p> Something bad happened, don't worry, its a feature.</p>{footer}</body</html>";
	private static final String fileDirectory = "<!DOCTYPE html><html><head><title>Index for: {path}</title></head>"
			+ "<body><h3>Index for: {path}</h3><hr>{files}{footer}</body></html>";
	
	//gettings for the templates, calls renderFooter() to dynamically insert footer based on WebServer constants
	public static String get400Page(){
		return renderFooter(_400);
	}
	public static String get404Page(){
		return renderFooter(_404);
	}

	public static String get403Page(){
		return renderFooter(_403);
	}

	public static String get500Page(){
		return renderFooter(_500);
	}
	
	//renders the footer template 
	private static String renderFooter(String template){
		return template.replace("{footer}", "<hr><p>Powered by " + WebServer.getServerName() + " (" + System.getProperty("os.name") 
				+ ") <br><i>" + WebServer.getServerDesc() +"</i></p>");
	}
	
	/**
	 * 
	 * @param folder File object representing a folder
	 * @param webPath relative webPath representing the location of the folder
	 * @return String template view for Directory listing
	 * Method dynamically enumerates the files and folders in a folder and renders it to a String for the response object
	 */
	public static String getFolderPage(File folder, String webPath){
		String template = fileDirectory;
		template = template.replace("{path}", webPath);
		template = renderFooter(template);
		StringBuilder temp = new StringBuilder();
		if(!webPath.equals("/")){
			temp.append("<li> <a href=\"../\"> Parent Directory </a> </li>");
		}
		File[] files = folder.listFiles();
		int ignored = 0;
		for(File f: files){
			String ext = Router.getFileExtension(f.getName());
			if(!WebServer.getHiddenFileTypes().contains(ext)){
				temp.append(generateHtmlLinkForFile(f, webPath));
			} else {
				ignored += 1;
			}
		}
		template = template.replace("{files}", String.format("<ul> %s </ul> %s files ignored (%s)",
				temp.toString(), ignored, WebServer.getHiddenFileTypes().toString()));
		return template;
	}
	
	//used to create the links to files and folders for the file directory enumeration
	private static String generateHtmlLinkForFile(File f, String path){
		return String.format("<li> %s <a href=\"%s\"> %s </a> </li>",
				f.isDirectory() ? "[Folder]" : "[File]", 
						f.isDirectory() ? f.getName()+"/" : f.getName(), f.getName(), f.getName());
	}
	
}

/**
 * @class Router
 * The controller that handles the formatting of the HttpResponse object based on the path from the HttpRequest object
 */
class Router {
	
	//absolute value of the web folder on the file system
	private String webRoot;
	
	public Router(String webRoot){
		this.webRoot = webRoot;
	}
	
	/**
	 * @param file object representing the Folder
	 * @param webPath relative path of the folder
	 * @param request HttpRequest object containing information about the request from client
	 * @param response HttpResponse object that will be used to to format a response to the client
	 * This method handles a path request that is a folder
	 */
	private void handleFolder(File file, String webPath, HttpRequest request, HttpResponse response){
		if(file.canRead() && (!WebServer.getForbiddenFileDirectories().contains(webPath))){
			String t = Template.getFolderPage(file, webPath);
			if(!webPath.endsWith("/")){
				response.setHttpCode(HttpCode._301);
				String url = "Http://" + request.getHeaders().get("Host").trim() + webPath + "/";
				response.setLocation(url);
			} else {
				response.setHttpCode(HttpCode._200);
			}
			response.setBody(t);
		} else {
			response.setHttpCode(HttpCode._403);
			response.setBody(Template.get403Page());
		}
		response.setContentType("text/html");
	}
	
	//creates a 500 HttpResponse object
	public void handleError(HttpResponse response){
		response.setHttpCode(HttpCode._500);
		response.setContentType("text/html");
		response.setBody(Template.get500Page());
	}

	/** 
	 * @param filePath absolute file path of the requested CGI file
	 * @param request HttpRequest object containing information about request from client
	 * @param response HttpResponse object used to format response to client
	 * @throws IOException
	 * Delegates a CGI file request from client based on type of request
	 */
	private void handleCGI(String filePath, HttpRequest request, HttpResponse response) throws IOException{
		if(request.isGet()){
			handleCGIGet(filePath, request, response);
		} else if (request.isPost()){
			handleCGIPost(filePath, request, response);
		} else {
			handle400Response(response);
		}
	}
	
	/**
	 * @param filePath absolute file path of the requested CGI file
	 * @param request HttpRequest object containing information about request from client
	 * @param response HttpResponse object used to format response to client
	 * @throws IOException
	 * Method will used a Runtime process to communicate and process the clients request based on GET params
	 * BufferedReader used to retrieve the process output and is formatted and passed to the HttpResponse object
	 */
	private void handleCGIGet(String filePath, HttpRequest request, HttpResponse response) throws IOException{
		String command = "/usr/bin/perl " + filePath;
		String[] envp = {"REQUEST_METHOD=GET", "QUERY_STRING="+request.getParams(), "HOME="+WebServer.getCGIHomeEnv()};
		Process process = Runtime.getRuntime().exec(command, envp);
		BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));

		String line = br.readLine();
		StringBuilder body = new StringBuilder();
		response.setContentType(line.split(":")[1]);
		while(line != null){
			line = br.readLine();
			if(line != null && line != ""){
				body.append(line+"\r\n");
			}
		}
		response.setBody(body.toString());
		response.setHttpCode(HttpCode._200);
	}
	
	/**
	 * @param filePath absolute file path of the requested CGI file
	 * @param request HttpRequest object containing information about request from client
	 * @param response HttpResponse object used to format response to client
	 * @throws IOException
	 * Method will use a Runtime process to communicate and process the clients request based on POST body
	 * DataOutputStream used to pass the POST body to the process, and BufferedReader to retrieve it
	 * response is formatted and passed to the HttpResponse object
	 */
	private void handleCGIPost(String filePath, HttpRequest request, HttpResponse response) throws IOException{
		String command = "/usr/bin/perl " + filePath;
		Map<String, String> headers = request.getHeaders();
		String[] envp = {"REQUEST_METHOD=POST", "QUERY_STRING=" + request.getParams(), "HOME=" + WebServer.getCGIHomeEnv(),
				"CONTENT_TYPE=" + headers.get("Content-Type"), "CONTENT_LENGTH=" + headers.get("Content-Length")};
		Process process = Runtime.getRuntime().exec(command, envp);
		BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
		DataOutputStream dos = new DataOutputStream(process.getOutputStream());
		
		dos.writeBytes(request.getBody());
		dos.close();
		String line = br.readLine();
		StringBuilder body = new StringBuilder();
		response.setContentType(line.split(":")[1]);
		while(line != null){
			line = br.readLine();
			if(line != null && line != ""){
				body.append(line+"\r\n");
			}
		}
		response.setBody(body.toString());
		response.setHttpCode(HttpCode._200);
	}
	
	/**
	 * @param file object representing the file requested by client
	 * @param response HttpResponse object used to format response to client
	 * Method for handling static files
	 */
	private void handleStaticFile(File file, HttpResponse response){
		response.setContentType(getFileContentType(file));
		response.setFile(file);
	}
	
	/**
	 * @param file object representing the file requested by client
	 * @return MIMEType
	 * basic implementation of MIMETypes for HttpResponse
	 */
	private String getFileContentType(File file){
		if(file.getName().matches("(.+)((\\.jpg)|(\\.jpeg)|(\\.png)|(\\.bmp)|(\\.gif))$")){
			return "image/" + Router.getFileExtension(file.getName());
		} else if(file.getName().matches("(.+)((\\.html)|(\\.css))$")){
			return "text/" + Router.getFileExtension(file.getName());
		} else if(file.getName().endsWith(".js")){
			return "text/javascript";
		} else if(file.getName().endsWith(".txt")){
			return "text/plain";
		} else {
			return "application/zip";
		}
	}
	
	//get file extension from name
	public static String getFileExtension(String fileName){
		String ext = "";
		int i = fileName.lastIndexOf('.');
		if(i>0){
			ext = fileName.substring(i+1, fileName.length());
		}
		return ext;
	}
	
	/**
	 * @param file object representing requested file
	 * @param filePath absolute file path for requested file on file system
	 * @param request HttpRequest object containing information about request from client
	 * @param response HttpResponse object used to format response to client
	 * Method for delegating task for file handling to appropriate methods based on whether it is a static file or CGIFile, as well as if 
	 * file has appropriate permissions
	 */
	private void handleFile(File file, String filePath, HttpRequest request, HttpResponse response){
		if(file.canRead()){
			response.setHttpCode(HttpCode._200);
			if(WebServer.getCGIFileExtension().equals(getFileExtension(file.getName()))){
				try {
					handleCGI(filePath, request, response);
				} catch (IOException e) {
					handleError(response);
					e.printStackTrace();
				}
			} else {
				handleStaticFile(file, response);
			}
		} else {
			handle404Response(response);
		}
	}
	
	//generates a 400 HttpResponse object
	private void handle400Response(HttpResponse response){
		response.setHttpCode(HttpCode._400);
		response.setBody(Template.get400Page());
		response.setContentType("text/html");
	}
	
	//generates a 404 HttpResponse object
	private void handle404Response(HttpResponse response){
		response.setHttpCode(HttpCode._404);
		response.setBody(Template.get403Page());
		response.setContentType("text/html");
	}
	
	/**
	 * @param request HttpRequest object containing information about request from client
	 * @param response HttpResponse object used to format response to client
	 * @return HttpResponse object used to send a formatted response to client
	 * method that handles primary delegation of task based on request from client to appropriate methods
	 * based on file type, folder type and request type
	 */
	public HttpResponse processRequest(HttpRequest request, HttpResponse response){
		if(request.isGet() | request.isPost()){
			String filePath = webRoot + request.getPath();
			File file = new File(filePath);
			if(file.isDirectory()){
				handleFolder(file, request.getPath(), request, response);
			} else if (!filePath.endsWith("/")){
				handleFile(file, filePath, request, response);
			} else {
				handle404Response(response);
			}
		} else {
			handle400Response(response);
		}
		return response;
	}
	
}

/**
 * @class HttpRequest
 * This class is used to represent the http request sent from the client to the server
 */
class HttpRequest {
	
	//self explanatory variables
	private String type;
	private String path;
	private String params;
	private String body;
	private String version;
	private Map<String, String> headers;
	private String ip;
	
	//private constructor, a static method is used to create new objects 
	private HttpRequest(String type, String path, String version, Map<String, String> headers, String ip, String body){
		this.type = type;
		this.path = path.contains("?") ? path.split("\\?")[0] : path;
		this.params = path.contains("?") ? path.split("\\?")[1] : "";
		this.version = version;
		this.headers = headers;
		this.ip = ip;
		this.body = body;
	}
	
	//self explanatory getter methods
	
	public String getType(){
		return type;
	}
	
	public boolean isPost(){
		return type.equals("POST");
	}
	
	public boolean isGet(){
		return type.equals("GET");
	}
	
	public String getPath(){
		return path;
	}
	
	public String getParams(){
		return params;
	}
	
	public String getVersion(){
		return version;
	}
	
	public String getIp(){
		return ip;
	}
	
	public String getBody(){
		return body;
	}
	
	public Map<String, String> getHeaders(){
		return headers;
	}

	/**
	 * @param client Socket object representing connection from client
	 * @return HttpRequest object containing information on the request from client
	 * @throws IOException
	 * so called factory method for creating HttpRequest object based on parsing input from the client Socket through a bufferedReader object
	 */
	public static HttpRequest ParseHttpRequest(Socket client) throws IOException{
		BufferedReader br = new BufferedReader(new InputStreamReader(client.getInputStream()));
		DataOutputStream dos = new DataOutputStream(client.getOutputStream());
		String line = br.readLine();
		if(line == null){
			throw new IOException();
		}
		String[] tokens = line.split(" ");
		String type = tokens[0];
		String path = tokens[1];
		String version = tokens[2];
		Map<String, String> headers = new HashMap<String, String>();
		while(!line.equals("")){
			line = br.readLine();
			tokens = line.split(":", 2);
			if(tokens.length >= 2) {
				headers.put(tokens[0], tokens[1].trim());
			}
		}
		
		//handles the retrieval of post body
		StringBuilder body = new StringBuilder();
		if(type.equals("POST")){
			int length = Integer.parseInt(headers.get("Content-Length"));
			dos.writeBytes("HTTP/1.1 200 OK\r\n");
			int recv = 0;
			while(recv < length){
				body.append((char) br.read());
				recv += 1;
			}
		}
		String ip = client.getInetAddress().toString();
		return new HttpRequest(type, path, version, headers, ip, body.toString());
	}
	
}

/**
 * @class HttpResponse
 * class that holds information that is collected and formatted for appropriate response to client based on request
 */
class HttpResponse {
	
	//self explanatory variables
	private static final String HTTPVERSION = "HTTP/1.1";
	private Socket client;
	private HttpCode code;
	private String body;
	private File file = null;
	private String contentType;
	private String location;
	
	
	private HttpResponse(Socket client){
		this.client = client;
	}
	
	//self explanatory getter and setter methods
	public void setHttpCode(HttpCode code){
		this.code = code;
	}
	
	public HttpCode getHttpCode(){
		return code;
	}
	
	public void setBody(String body){
		this.body = body;
	}
	
	public void setFile(File file){
		this.file = file;
	}
	
	public void setLocation(String location){
		this.location = location;
	}
	
	public void setContentType(String contentType){
		this.contentType = contentType;
	}
	
	//Method that sends the client a response based on collected response information in this object
	public void send() throws IOException {
		DataOutputStream dos = new DataOutputStream(client.getOutputStream());
		sendHttpCode(dos);
		sendServerName(dos);
		sendContentType(dos);
		sendContentLength(dos);
		sendBody(dos);
		dos.flush();
	}
	
	//sends Server name header
	private void sendServerName(DataOutputStream dos) throws IOException{
		dos.writeBytes(String.format("Server: %s\r\n", WebServer.getServerName()));
	}
	
	//sends http code header
	private void sendHttpCode(DataOutputStream dos) throws IOException{
		dos.writeBytes(String.format("%s %s\r\n", HTTPVERSION, code));
		if(code.equals(HttpCode._301)){
			dos.writeBytes(String.format("Location: %s\r\n", location));
		}
	}
	
	//sends content-type header
	private void sendContentType(DataOutputStream dos) throws IOException{
		dos.writeBytes(String.format("Content-Type: %s\r\n", contentType));
	}
	
	//sends content-length header, based on if response is a text response or a file response
	private void sendContentLength(DataOutputStream dos) throws IOException{
		if(file != null) {
			dos.writeBytes(String.format("Content-Length:  %s\r\n", file.length()));
		} else {
			dos.writeBytes(String.format("Content-Length:  %s\r\n", body.length()));
		}
	}
	
	//sends the body of the response based on if its a text response or file response
	private void sendBody(DataOutputStream dos) throws IOException {
		if(file != null) {
			sendFile(dos);
		} else {
			dos.writeBytes(String.format("\r\n%s\r\n", body));
		}
	}
	
	//sends the file response
	private void sendFile(DataOutputStream dos) throws IOException{
		byte[] buffer = new byte[1024];
		FileInputStream fis = new FileInputStream(file);
		int size = fis.read(buffer);
		dos.writeBytes("\r\n");
		while (size > 0) {
			dos.write(buffer, 0, size);
			size = fis.read(buffer);
		}
		fis.close();
	}
	
	//factory method for creating HttpResponse object
	//sends it to the router for collection of response information before returning
	public static HttpResponse createHttpResponse(Socket client, HttpRequest request, Router router){
		HttpResponse response = new HttpResponse(client);
		router.processRequest(request, response);
		return response;
	}
	
	//factory method for creating a 500 response
	public static HttpResponse create500Response(Socket client, Router router){
		HttpResponse response = new HttpResponse(client);
		router.handleError(response);
		return response;
	}
	
}


/**
 * @class Worker
 * worker class that implements the runnable interface
 * Handles the processing of an individual socket connection and http request
 */
class Worker implements Runnable {

    private Socket client = null;
	private Router router;
    
    public Worker(Socket clientSocket, Router router) {
        this.client = clientSocket;
        this.router = router;
    }
    
    //logging methods to print http requests completed
    private void logConnection(HttpRequest request, HttpResponse response){
    	String fullAddress = request.getHeaders().get("Host") + request.getPath();
    	String userAgent = request.getHeaders().get("User-Agent");
    	DateFormat dateFormat = new SimpleDateFormat("yyyy/MM/dd HH:mm:ss");
    	Date date = new Date();
    	System.out.printf("[%s] %s %s - %s (%s) - %s\r\n", request.getIp(), request.getType(), response.getHttpCode(), fullAddress.trim(), userAgent.trim(), dateFormat.format(date));
    }
    
    /**
     * Main run() method for the worker thread
     * Creates a HttpRequest object from the client request
     * Creates a HttpResponse object based on th HttpRequest object
     * uses response object to send the response to client
     * try catch blocks here are the main error handling components of this webserver
     */
    public void run() {
        try {
			HttpRequest request = HttpRequest.ParseHttpRequest(client);
			HttpResponse response = HttpResponse.createHttpResponse(client, request, router);
			response.send();
			logConnection(request, response);
            client.close();
        } catch (IOException e) {
        	System.out.println("An Error has occured while processing the request, will attempt to send a 500 response");
            e.printStackTrace();
            HttpResponse response = HttpResponse.create500Response(client, router);
            try {
	            response.send();
	            client.close();
            } catch(IOException i){
            	System.out.println("Failed to send 500, client most likely disconnected");
            	i.printStackTrace();
            }
        } catch (Exception ee){
        	System.out.println("Caught an unexpected error!");
        	ee.printStackTrace();
        }
    }
}

/**
 * @class WebServer
 * the main WebServer class
 * receivings incoming socket connections and delegates them to a worker class started in a new thread
 */
class WebServer {

	//WebServer constants
	private static final String serverName = "DogeWebServer/0.1";
	private static final String serverDesc = "So WebServer, Much Enterprise, Wow.";
	
	private static String CGIFileExtension;
	private static String CGIHomeEnv;
	private static List<String> hiddenFileTypes;
	private static List<String> forbiddenFileDirectories; 
			
	private Router router;
	private Integer port;
	private ServerSocket serverSocket;
	
	public WebServer(Integer port, String webRoot, String CGIFileExtension, String CGIHomeEnv, List<String> hiddenFileTypes, List<String> forbiddenFileDirectories){
		this.port = port;
		this.router = new Router(webRoot);
		
		WebServer.CGIFileExtension = CGIFileExtension;
		WebServer.CGIHomeEnv = CGIHomeEnv;
		WebServer.hiddenFileTypes = hiddenFileTypes;
		WebServer.forbiddenFileDirectories = forbiddenFileDirectories;
	}
	
	//self explanatory getter methods
	
	public static String getServerName(){
		return serverName;
	}
	
	public static String getServerDesc(){
		return serverDesc;
	}
	
	public static String getCGIFileExtension(){
		return CGIFileExtension;
	}
	
	public static String getCGIHomeEnv(){
		return CGIHomeEnv;
	}
	
	public static List<String> getHiddenFileTypes(){
		return hiddenFileTypes;
	}
	
	public static List<String> getForbiddenFileDirectories(){
		return forbiddenFileDirectories;
	}

	//main server() loop
	//starts a new thread for every new request
    public void serve(){
        startListening();
        while(true){
            try {
                new Thread(
                        new Worker(this.serverSocket.accept(), router)
                ).start();
            } catch (IOException e) {
                throw new RuntimeException("Error accepting client connection", e);
            }
        }
    }

    //to start listening of socket, try catch incase socket in use
    private void startListening() {
        try {
            this.serverSocket = new ServerSocket(this.port);
        } catch (IOException e) {
            throw new RuntimeException("Cannot open port " + this.port, e);
        }
    }

	public static void main(String args[]) {
		//driver main methods
		//takes in port from args if available if not default port is used
		
		//configuration variables
		String CGI_FILE_EXTENSION = "pl";	
		String WEB_ROOT = System.getProperty("user.dir");
		String CGI_HOME_ENV = WEB_ROOT.substring(0, WEB_ROOT.lastIndexOf("/"));

		List<String> HIDDEN_FILE_TYPES = Arrays.asList("java", "class");
		List<String> FORBIDDEN_FILE_DIRECTORIES = Arrays.asList("/forbidden");
		Integer PORT = 21215;
		
		if(args.length > 0 ){
			try {
				PORT = Integer.parseInt(args[0]);
			} catch(InputMismatchException e) {
				System.out.println("port must be a number!");
			}
		} else {
			System.out.println("No port provided, using default port "+PORT);
		}
		
		//create WebServer object
		WebServer webServer = new WebServer(PORT, WEB_ROOT, CGI_FILE_EXTENSION, CGI_HOME_ENV, HIDDEN_FILE_TYPES, FORBIDDEN_FILE_DIRECTORIES);
		System.out.printf("%s started on port %s serving %s\r\n", WebServer.getServerName(), PORT, WEB_ROOT);
		//start serving!
		webServer.serve();
	}
}
