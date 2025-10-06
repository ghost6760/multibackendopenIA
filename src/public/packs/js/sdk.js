<<'JS'
/*
  Minimal test SDK for integration debugging.
  Exposes window.chatwootSDK.run() and fires chatwoot:ready.
*/
(function(){
  if (window.chatwootSDK) return; // evitar doble carga
  window.chatwootSDK = {
    run: function(opts){
      try {
        console.log('[minimal-sdk] run called with', opts);
        window.chatwootSDK._lastRun = opts || {};
        // simula inicialización y dispara chatwoot:ready
        setTimeout(function(){
          try {
            const ev = new Event('chatwoot:ready');
            window.dispatchEvent(ev);
            console.log('[minimal-sdk] dispatched chatwoot:ready');
          } catch(e){ console.warn('[minimal-sdk] ready dispatch failed', e); }
        }, 100);
      } catch(e){
        console.error('[minimal-sdk] run error', e);
      }
    },
    getUrl: function(){ 
      return (window.chatwootSDK._lastRun && window.chatwootSDK._lastRun.baseUrl) || window.location.origin;
    },
    createFrame: function(){ console.warn('[minimal-sdk] createFrame called (noop)'); }
  };
})();
JS
