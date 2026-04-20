const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('applybotDesktop', {
  version: '0.1.0',
})
