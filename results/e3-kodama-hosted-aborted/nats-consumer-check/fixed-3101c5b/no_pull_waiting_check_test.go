package queue

// Check for the paper (not committed): Kodama 3101c5b's Consume after its
// consumer is deleted while no pull request is waiting. That is the case
// that gave "no heartbeat received" for good with the old loop (pilot, and
// 70dcabb's second e attempt). Run: go test -run TestCheckNoPullWaiting -v.

import (
	"context"
	"testing"
	"time"
)

func TestCheckNoPullWaiting(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 150*time.Second)
	defer cancel()
	t0 := time.Now()
	logf := func(format string, a ...any) {
		t.Logf("%6.1fs "+format, append([]any{time.Since(t0).Seconds()}, a...)...)
	}
	js := startJetStream(t)
	if err := Ensure(ctx, js); err != nil {
		t.Fatal(err)
	}
	msgs, err := Consume(ctx, js, EmbeddingsStream, EmbedConvConsumer, "check")
	if err != nil {
		t.Fatal(err)
	}
	defer msgs.Stop()

	if err := PublishEmbed(ctx, js, EmbedConvSubject, "row-1"); err != nil {
		t.Fatal(err)
	}
	msg, err := msgs.Next(ctx)
	if err != nil {
		t.Fatal(err)
	}
	logf("got %s; the handler now holds it for 40 s, so no pull request is sent", msg.Data())
	time.Sleep(33 * time.Second) // the iterator's 30 s pull request has expired
	if err := js.DeleteConsumer(ctx, EmbeddingsStream, EmbedConvConsumer); err != nil {
		t.Fatal(err)
	}
	logf("consumer deleted while no pull request was waiting")
	time.Sleep(7 * time.Second)
	_ = msg.Ack()
	if err := PublishEmbed(ctx, js, EmbedConvSubject, "row-2"); err != nil {
		t.Fatal(err)
	}
	logf("handler done; row-2 published; calling Next")
	// row-1's ack went to the deleted consumer, so the work queue delivers
	// row-1 again (at least once); Kodama's embed handlers skip rows that
	// already have an embedding. Read until row-2 arrives.
	for {
		msg, err = msgs.Next(ctx)
		if err != nil {
			t.Fatalf("Next: %v", err)
		}
		logf("got %s", msg.Data())
		_ = msg.Ack()
		if string(msg.Data()) == `{"id":"row-2"}` {
			break
		}
	}
	cons, err := js.Consumer(ctx, EmbeddingsStream, EmbedConvConsumer)
	if err != nil {
		t.Fatal(err)
	}
	logf("consumer exists again, durable=%q", cons.CachedInfo().Config.Durable)
}
