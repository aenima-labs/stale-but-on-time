// What does Kodama's consumer loop log when the server deletes its consumer,
// (T1) while a pull request is waiting, and (T2) while none is waiting? And
// does the loop ever recover? Same consumer config and loop as Kodama 70dcabb.
package main

import (
	"context"
	"fmt"
	"os"
	"strconv"
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
	dir, _ := os.MkdirTemp("", "natsexp2")
	defer os.RemoveAll(dir)
	ns, _ := natsserver.NewServer(&natsserver.Options{JetStream: true, StoreDir: dir, NoLog: true, NoSigs: true, Port: -1})
	ns.Start()
	ns.ReadyForConnections(10 * time.Second)
	nc, _ := nats.Connect(ns.ClientURL())
	js, _ := jetstream.New(nc)
	ctx := context.Background()

	run := func(name, stream, subj string, holdFirst time.Duration, deleteAt time.Duration, recreateAt time.Duration) {
		js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{Name: stream, Subjects: []string{subj}, Storage: jetstream.FileStorage, Retention: jetstream.WorkQueuePolicy})
		cfg := jetstream.ConsumerConfig{Name: "c", FilterSubject: subj, DeliverPolicy: jetstream.DeliverAllPolicy, AckPolicy: jetstream.AckExplicitPolicy, AckWait: 30 * time.Second, MaxDeliver: 5, MaxAckPending: 16}
		js.CreateOrUpdateConsumer(ctx, stream, cfg)
		cons, _ := js.Consumer(ctx, stream, "c")
		it, _ := cons.Messages()
		start := time.Now()
		got := 0
		go func() {
			last := ""
			for {
				msg, err := it.Next()
				if err != nil {
					if err.Error() != last {
						logf("%s next error: %v", name, err)
						last = err.Error()
					}
					time.Sleep(time.Second)
					continue
				}
				last = ""
				got++
				hold, _ := strconv.Atoi(string(msg.Data()))
				logf("%s got message, handler holds %d ms", name, hold)
				time.Sleep(time.Duration(hold) * time.Millisecond)
				msg.Ack()
			}
		}()
		// first message, optionally held long
		js.Publish(ctx, subj, []byte(strconv.Itoa(int(holdFirst.Milliseconds()))))
		time.Sleep(deleteAt - time.Since(start))
		logf("%s deleting consumer (as NATS does for an inactive non-durable one)", name)
		js.DeleteConsumer(ctx, stream, "c")
		time.Sleep(recreateAt - time.Since(start))
		logf("%s recreating consumer and publishing 3 messages (as a Kodama restart would)", name)
		js.CreateOrUpdateConsumer(ctx, stream, cfg)
		for i := 0; i < 3; i++ {
			js.Publish(ctx, subj, []byte("10"))
		}
		time.Sleep(70*time.Second + recreateAt - time.Since(start))
		logf("%s end: messages handled %d of 4", name, got)
	}
	done := make(chan bool)
	go func() { run("T1 pull waiting ", "S1", "s1.x", 10*time.Millisecond, 5*time.Second, 10*time.Second); done <- true }()
	go func() { run("T2 none waiting ", "S2", "s2.x", 40*time.Second, 33*time.Second, 50*time.Second); done <- true }()
	<-done
	<-done
}
