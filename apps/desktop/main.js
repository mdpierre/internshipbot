const { app, BrowserWindow } = require('electron')
const { spawn } = require('child_process')
const http = require('http')
const path = require('path')

const ROOT = path.resolve(__dirname, '..', '..')
const WEB_DIR = path.join(ROOT, 'apps', 'web')
const API_DIR = path.join(ROOT, 'apps', 'api')
const WEB_URL = process.env.APPLYBOT_WEB_URL || 'http://localhost:3000'
const API_URL = process.env.APPLYBOT_API_URL || 'http://localhost:8000/health'

let webProcess = null
let apiProcess = null

function ping(url) {
  return new Promise((resolve) => {
    http.get(url, (res) => {
      res.resume()
      resolve(res.statusCode && res.statusCode < 500)
    }).on('error', () => resolve(false))
  })
}

async function waitFor(url, timeoutMs = 30000) {
  const startedAt = Date.now()
  while (Date.now() - startedAt < timeoutMs) {
    if (await ping(url)) return true
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  return false
}

function startApi() {
  apiProcess = spawn(
    process.env.APPLYBOT_API_BIN || 'python3',
    ['-m', 'uvicorn', 'app.main:app', '--port', '8000'],
    {
      cwd: API_DIR,
      stdio: 'inherit',
      env: { ...process.env },
    }
  )
}

function startWeb() {
  const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'
  webProcess = spawn(
    process.env.APPLYBOT_WEB_BIN || npmCmd,
    ['run', 'dev'],
    {
      cwd: WEB_DIR,
      stdio: 'inherit',
      env: { ...process.env },
    }
  )
}

async function ensureServices() {
  if (!(await ping(API_URL))) startApi()
  if (!(await ping(WEB_URL))) startWeb()
  await waitFor(API_URL)
  await waitFor(WEB_URL)
}

async function createWindow() {
  await ensureServices()
  const win = new BrowserWindow({
    width: 1440,
    height: 980,
    minWidth: 1100,
    minHeight: 760,
    title: 'applybot desktop',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  await win.loadURL(WEB_URL)
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  for (const child of [webProcess, apiProcess]) {
    if (child && !child.killed) {
      child.kill()
    }
  }
})
