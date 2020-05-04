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
import java.util.concurrent.TimeUnit;

public final class EasyNonOOM
{
    public static void main(String[] args)
    {
        List<Object> list = new ArrayList<>();
        double goodZone = 0.25 * Runtime.getRuntime().maxMemory();
        System.out.println(String.format(
            "Not triggering OutOfMemory by only allocating %.2f bytes",
            goodZone
        ));

        long start = System.nanoTime();
        long end = 0;
        try {
            while (true) {
                if (list.size() * 1024 * 1024 < goodZone)
                {
                    byte[] bytes = new byte[1024 * 1024];
                    list.add(bytes);
                }
                if (TimeUnit.NANOSECONDS.toSeconds(System.nanoTime() - start) > 10)
                    break;
            }
        }
        catch (Exception t) {
            System.out.println(t.toString());
        }
        System.out.println("final list size: " + list.size());
    }
}
