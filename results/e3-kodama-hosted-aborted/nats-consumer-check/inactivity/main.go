// Does a JetStream consumer declared like Kodama's (Name, no Durable) get
// deleted by the server while the consumer loop is busy in its handler?
//
// Each scenario uses its own stream and consumer, the same config and the
// same loop as Kodama 70dcabb (internal/queue/jetstream.go,
// internal/app/pipeline/pipeline.go runEmbedConsumer). Messages carry the
// handler's duration in ms.
package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
	"sync"
	"time"

	natsserver "github.com/nats-io/nats-server/v2/server"
	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

var t0 = time.Now()

func logf(format string, a ...any) {
	fmt.Printf("%6.1fs "+format+"\n", append([]any{time.Since(t0).Seconds()}, a...)...)
}

func main() {
	dir, _ := os.MkdirTemp("", "natsexp")
	defer os.RemoveAll(dir)
	ns, err := natsserver.NewServer(&natsserver.Options{JetStream: true, StoreDir: dir, NoLog: true, NoSigs: true, Port: -1})
	if err != nil {
		panic(err)
	}
	ns.Start()
	if !ns.ReadyForConnections(10 * time.Second) {
		panic("not ready")
	}
	nc, err := nats.Connect(ns.ClientURL())
	if err != nil {
		panic(err)
	}
	js, _ := jetstream.New(nc)
	ctx := context.Background()

	// name, durable?, handler durations (ms) published at given offsets (s)
	type job struct {
		at   float64
		hold int
	}
	scenarios := []struct {
		name    string
		durable bool
		jobs    []job
		watch   float64
	}{
		{"idle-60s", false, nil, 60},
		{"hold-3s", false, []job{{1, 3000}}, 45},
		{"hold-10s", false, []job{{1, 10000}}, 45},
		{"hold-10s-late", false, []job{{25, 10000}}, 60},
		{"hold-35s", false, []job{{1, 35000}}, 60},
		{"hold-35s-durable", true, []job{{1, 35000}}, 60},
	}
	var wg sync.WaitGroup
	for i, s := range scenarios {
		wg.Add(1)
		go func(i int, s struct {
			name    string
			durable bool
			jobs    []job
			watch   float64
		}) {
			defer wg.Done()
			stream := fmt.Sprintf("S%d", i)
			subj := fmt.Sprintf("s%d.pending", i)
			if _, err := js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{Name: stream, Subjects: []string{subj}, Storage: jetstream.FileStorage, Retention: jetstream.WorkQueuePolicy, Duplicates: 5 * time.Minute}); err != nil {
				panic(err)
			}
			cfg := jetstream.ConsumerConfig{Name: "c", FilterSubject: subj, DeliverPolicy: jetstream.DeliverAllPolicy, AckPolicy: jetstream.AckExplicitPolicy, AckWait: 30 * time.Second, MaxDeliver: 5, MaxAckPending: 16}
			if s.durable {
				cfg.Durable = "c"
			}
			if _, err := js.CreateOrUpdateConsumer(ctx, stream, cfg); err != nil {
				panic(err)
			}
			start := time.Since(t0).Seconds()
			cons, _ := js.Consumer(ctx, stream, "c")
			it, _ := cons.Messages()
			go func() { // Kodama's loop
				errs := 0
				for {
					msg, err := it.Next()
					if err != nil {
						errs++
						if errs <= 2 {
							logf("%-17s next error: %v", s.name, err)
						}
						time.Sleep(time.Second)
						continue
					}
					hold, _ := strconv.Atoi(string(msg.Data()))
					logf("%-17s handler holds %d ms", s.name, hold)
					time.Sleep(time.Duration(hold) * time.Millisecond)
					_ = msg.Ack()
				}
			}()
			for _, j := range s.jobs {
				go func(j job) {
					time.Sleep(time.Duration(j.at * float64(time.Second)))
					_, _ = js.Publish(ctx, subj, []byte(strconv.Itoa(j.hold)))
				}(j)
			}
			deleted := false
			for time.Since(t0).Seconds()-start < s.watch {
				time.Sleep(500 * time.Millisecond)
				if _, err := js.Consumer(ctx, stream, "c"); err != nil && !deleted {
					deleted = true
					logf("%-17s consumer gone: %v", s.name, err)
				}
			}
			logf("%-17s end: deleted=%v", s.name, deleted)
		}(i, s)
	}
	wg.Wait()
}
