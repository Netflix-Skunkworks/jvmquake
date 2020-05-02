/**
 * Copyright 2019 Netflix, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import java.util.ArrayList;
import java.util.List;

public final class EasyThreadOOM
{
    public static void main(String[] args)
            throws Exception
    {
        System.out.println("Thread ~fork bombing the JVM ...");
        List<Thread> list = new ArrayList<>();
        try {
            for (int i = 0; i < 16777216; i++) {
                Thread thread = new Thread(() -> {
                    while (true) {
                        try {
                            Thread.sleep(10000);
                        } catch (InterruptedException ign) {}
                    }
                });
                thread.start();
                // Hold onto the thread
                list.add(thread);
            }
        }
        catch (Exception t) {
            System.out.println(t.toString());
        } finally {
            System.out.println("final list size: " + list.size());
        }
    }
}
