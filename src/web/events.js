export function createEventStream({ url, onEvent }) {
  let source = null;

  const start = () => {
    if (source) return;
    source = new EventSource(url);
    source.onmessage = (msg) => {
      try {
        const envelope = JSON.parse(msg.data);
        onEvent(envelope);
      } catch (_) {}
    };
    source.onerror = () => {
      stop();
      setTimeout(() => start(), 700);
    };
  };

  const stop = () => {
    if (!source) return;
    try {
      source.close();
    } catch (_) {}
    source = null;
  };

  return { start, stop };
}

