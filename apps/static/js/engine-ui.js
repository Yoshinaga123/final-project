// Engine UI Controller: single hot path for applying engine bestmove to UI
// - Normalizes moves
// - Deduplicates by {move, ply}
// - Validates via adapter.isLegal
// - Applies via adapter.apply
// - Handles special moves and resync on failure

(function(global){
  'use strict';

  class EngineBestmoveController {
    constructor(opts){
      this.adapter = (opts && opts.adapter) || {};
      this.lastApplied = null; // { move, ply }
      this.stats = {
        received: 0,
        applied: 0,
        suppressed: 0,
        failedIllegal: 0,
        resyncRequested: 0,
        specials: 0
      };
    }

    normalize(raw){
      if (!raw) return null;
      return String(raw).trim().replace(/^bestmove\s+/i, '').split(/\s+/)[0];
    }

    onBestmove(raw){
      const mv = this.normalize(raw);
      this.stats.received++;
      const log = this.adapter.log || (()=>{});
      const markThinking = this.adapter.markThinking || (()=>{});

      if (!mv) { 
        log('🤖 bestmove: (none)');
        markThinking(false);
        return;
      }

      // Special bestmoves
      if (mv === 'resign' || mv === 'win'){
        this.stats.specials++;
        try { (this.adapter.onSpecialMove||(()=>{}))(mv); } catch(_){}
        markThinking(false);
        return;
      }

      // Dedup by {move, ply}
      let ply = 0;
      try { ply = Number((this.adapter.getPly && this.adapter.getPly()) || 0); } catch(_){}
      if (this.lastApplied && this.lastApplied.move === mv && this.lastApplied.ply === ply){
        this.stats.suppressed++;
        log(`↩️ 重複bestmoveをスキップ: ${mv} (ply=${ply})`);
        markThinking(false);
        return;
      }

      // Decide mover side based on state
      let sideToMove = 'b';
      try { sideToMove = (this.adapter.getSideToMove && this.adapter.getSideToMove()) || 'b'; } catch(_){}
      const moverSide = (sideToMove === 'b') ? 'w' : 'b';

      // Validate quickly before apply
      try {
        if (this.adapter.isLegal && !this.adapter.isLegal(mv)){
          this.stats.failedIllegal++;
          log(`⛔ 非合法(エンジン手・事前弾き): ${mv}`);
          this._requestResync();
          markThinking(false);
          return;
        }
      } catch(_){}

      // Apply to board
      const ok = (this.adapter.apply && this.adapter.apply(mv, moverSide)) || false;
      if (!ok){
        this.stats.failedIllegal++;
        log(`❌ エンジン手の適用失敗: ${mv}`);
        this._requestResync();
        markThinking(false);
        return;
      }

      // Record success and push KIF
      try { (this.adapter.pushKif||(()=>{}))(mv, moverSide); } catch(_){}
      this.lastApplied = { move: mv, ply };
      this.stats.applied++;

      // Advance turn indicator (UI owns view-only; authority remains server)
      try { (this.adapter.flipTurn||(()=>{}))('b'); } catch(_){}

      markThinking(false);
      try { (this.adapter.setBoardEnabled||(()=>{}))(true); } catch(_){}
    }

    _requestResync(){
      this.stats.resyncRequested++;
      try { (this.adapter.requestState||(()=>{}))(); } catch(_){}
    }

    getStats(){
      return { ...this.stats, lastApplied: this.lastApplied ? { ...this.lastApplied } : null };
    }

    resetDedup(){
      this.lastApplied = null;
    }
  }

  // UMD-ish export
  if (typeof module !== 'undefined' && module.exports){
    module.exports = EngineBestmoveController;
  }
  global.EngineBestmoveController = EngineBestmoveController;
})(typeof window !== 'undefined' ? window : globalThis);
